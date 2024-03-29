from models.order.order_model import OrderData, Order, OrderItemData, OrderItem, OrderStatusType
from models.order.order_flow import OrderFlowFactory, IOrderFlow, OrderFlowType
from uow.uow_order import UowOrder
from service.logistics_service import LogisticsService,LogisticsStatus
from service.payment_service import PaymentService, PaymentType, PaymentStatus
from service.inventory_service import InventoryService
from datetime import datetime
from typing import List
import json

# Custom JSON encoder for datetime objects
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, OrderItem):
            return obj.__dict__
        return super(CustomEncoder, self).default(obj)


class OrderService:

    def __init__(self):
        self.logistics_service = LogisticsService()
        self.payment_service = PaymentService()
        self.inventory_service = InventoryService()
    
    def place_order(self, data, uow:UowOrder):
        
        order_data = OrderData(**data) # verfiy order data struct is match
        
        with uow:
            # create order id
            order_id = self.__create_new_order_id(uow)

            # create new order
            order = self.__create_order(order_id, order_data)
            uow.order_repo.add_order(order)

            # create order items
            order_items = self.__create_all_order_items(order, order_data.order_items, uow)
            order.set_order_items(order_items)

            # update order total_amount
            order.calculate_total_amount()
            uow.order_repo.update_order_data(order.order_id, 'total_amount', order.total_amount)

            # process orderflow
            self.__process_orderflow(order)

            uow.commit()

        return json.dumps(order, cls=CustomEncoder, indent=None)

    def __create_new_order_id(self, uow:UowOrder):
        # get next order id from repo
        order_id = uow.order_repo.get_next_order_id()
        # check order_id is been used or not 
        order = uow.order_repo.get_order(order_id)

        if order is not None:
            raise Exception(f'Order id {order_id} has been used')
        else:
            return order_id

    def __create_order(self, order_id, order_data:OrderData):
        # create new order 
        order = Order(
            order_id=order_id, 
            user_id=self.__get_user_id(), 
            order_status=OrderStatusType.PENDING,
            order_date=datetime.now(), 
            total_amount=0,
            contact_phone=order_data.contact_phone,
            email=order_data.email, 
            shipping_method=order_data.shipping_method,
            shipping_address=order_data.shipping_address,
            shipping_status= LogisticsStatus.PENDING,
            payment_method=order_data.payment_method, 
            payment_status=PaymentStatus.PENDING,
            payment_date=None,
        ) 

        return order

    def __create_all_order_items(self, order:Order, order_item_data: List[OrderItemData], uow:UowOrder):
        order_items : List[OrderItem] = []
    
        for item in order_item_data:
            order_item_id = uow.order_repo.get_next_order_item_id()
            order_item = OrderItem(order_item_id, order.user_id, order.order_id,
                                   **item)
            order_items.append(order_item)
            uow.order_repo.add_order_item(order_item)

        return order_items

    def __process_orderflow(self, order:Order):
        orderflow_class = self.__select_orderflow(order.payment_method)
        orderflow : IOrderFlow = orderflow_class(self.payment_service, 
                                                 self.inventory_service, 
                                                 self.logistics_service)
        #process orderflow
        try:
             orderflow.process_orderflow(order)
             return 'Order is processing'
        except Exception as e:
            raise Exception(f'Error: {e}')

    def __select_orderflow(self, payment_method:PaymentType):
        if payment_method == PaymentType.COD.value:
            return OrderFlowFactory.create_orderflow(OrderFlowType.COD.value)
        else:
            return OrderFlowFactory.create_orderflow(OrderFlowType.PREPAID.value)


    def get_user_orders(self, user_id, uow:UowOrder):
        with uow:
            orders:List[Order] = uow.order_repo.list_order_by_user_id(user_id)
            for o in orders:
                o.order_items = uow.order_repo.list_order_items_by_order_id(o.order_id)
            order_dicts = [order.__dict__ for order in orders]
            uow.commit()
        return json.dumps(order_dicts, cls=CustomEncoder, indent=None)

    def update_payment_status(self, data, uow:UowOrder):
        if not isinstance(data['order_id'], int):
            raise Exception('Data is invalid')
        
        if not isinstance(data['payment_status'], int):
            raise Exception('Data is invalid')  
        
        order_id = data['order_id']
        payment_status = PaymentStatus(data['payment_status'])
        with uow:
            order = self.__get_order(order_id, uow)
            order.update_payment_status(payment_status.value)
            uow.order_repo.update_order_data(order_id,'payment_status' , payment_status.value)
            uow.commit()
        order_json = json.dumps(order.__dict__, cls=CustomEncoder, indent=None)
        return order_json

    def update_shipping_stauts(self, data, uow:UowOrder):
        if not isinstance(data['order_id'], int):
            raise Exception('Data is invalid')
        
        if not isinstance(data['shipping_status'], int):
            raise Exception('Data is invalid')  
        
        order_id = data['order_id']
        shipping_status = LogisticsStatus(data['shipping_status'])
        with uow:
            order = self.__get_order(order_id, uow)         
            order.update_shipping_status(shipping_status.value)
            uow.order_repo.update_order_data(order_id,'shipping_status' , shipping_status.value)
            uow.commit()

        order_json = json.dumps(order.__dict__, cls=CustomEncoder, indent=None)
        return order_json

    def update_order_status(self, data, uow:UowOrder):
        if not isinstance(data['order_id'], int):
            raise Exception('Data is invalid')
        
        if not isinstance(data['order_status'], int):
            raise Exception('Data is invalid')  
        
        order_id = data['order_id']
        order_status = OrderStatusType(data['order_status'])
        with uow:
            order = self.__get_order(order_id, uow)
            order.update_order_status(order_status)
            uow.order_repo.update_order_data(order_id, 'order_status' , order_status.value)
            uow.commit()
        order_json = json.dumps(order.__dict__, cls=CustomEncoder, indent=None)
        return order_json
    
    def __get_order(self, order_id, uow:UowOrder):  
        order:Order = uow.order_repo.get_order(order_id)
        order.set_order_items(uow.order_repo.list_order_items_by_order_id(order_id))
        return order