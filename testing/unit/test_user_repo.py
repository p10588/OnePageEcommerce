import pytest
from db.user_repo_postgres import UserRepo_postgres
from models.auth_model import User

test_user_id = 'test_user'
def test_add_new_user():
    user = User(
        user_id = test_user_id,
        full_name='sample name',
        account='aaa',
        email='aaa@aaa.com',
        shipping_address='qwertyuiop',
        contact_phone='88612345678'
    )
    try:
        user_repo = UserRepo_postgres()
        user_repo.add_new_user(user)
        assert True
    except Exception as e:
        print(e)
        assert False

def test_update_user_data():
    try:
        user_repo = UserRepo_postgres()
        user_repo.update_user_data(test_user_id, 'full_name', 'vvv')
        assert True
    except Exception as e:
        print(e)
        assert False

def test_get_user():
    try:
        user_repo = UserRepo_postgres()
        user = user_repo.get_user(test_user_id)
        print(user.account)
        assert user.email == 'aaa@aaa.com'
    except Exception as e:
        print(e)
        assert False

def remove_user():
    user_repo = UserRepo_postgres()
    user_repo.remove_user(test_user_id)