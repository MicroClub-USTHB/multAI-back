from typing import AsyncIterator

from db.generated import devices as device_queries
from app.core.securite import  create_totp_secret
import uuid
from app.core.exceptions import DBException,AppException
from db.generated.models import UserDevice


class DeviceService:
    device_querier: device_queries.AsyncQuerier

    def init(self, device_querier: device_queries.AsyncQuerier):
        self.device_querier = device_querier
    @staticmethod
    async def create_device(user_id: uuid.UUID,device_name: str,device_type: str)->UserDevice|None:
        try :
            if await DeviceService.device_querier.count_user_devices(user_id=user_id) >= 3:
                raise AppException.bad_request("You can only have 3 devices")

            return await DeviceService.device_querier.create_device(
                user_id=user_id,
                device_name=device_name,
                device_type=device_type,
                totp_secret=create_totp_secret(),
            )
        except Exception as e :
            DBException.handle(e)
            
    @staticmethod
    async def revoke_device(device_id:uuid.UUID,user_id :uuid.UUID):
        try :
            #here were cacscading the delete of the session  no need to handle it 
            await DeviceService.device_querier.revoke_device(
                id=device_id,
                user_id=user_id
            )
        except Exception as e :
            DBException.handle(e)
    
    @staticmethod
    async def get_all_devices(user_id:uuid.UUID)->tuple(AsyncIterator[UserDevice],int)
        devices= DeviceService.device_querier.list_user_devices(user_id=user_id)
        count = await DeviceService.device_querier.count_user_devices(user_id=user_id)
        return devices,count

    @staticmethod
    async def get_device_by_id(device_id:uuid.UUID,user_id:uuid.UUID)->UserDevice|None:
        try :
            return await DeviceService.device_querier.get_device_by_id(id=device_id,user_id=user_id)
        except Exception as e :
            DBException.handle(e)

    @staticmethod
    async  def count_devices(user_id:uuid.UUID)->int:
        try :
            return await DeviceService.device_querier.count_user_devices(user_id=user_id)
        except Exception as e :
            DBException.handle(e)
    
    
        
        
    

    