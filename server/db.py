# db.py
# Database management.
# See: https://sqlmodel.tiangolo.com/ for ORM background.

import pandas as pd
import logging
import datetime as dt

from sqlmodel import Field, SQLModel, create_engine, Session, select
from typing import Optional, Union, List

# Logging config
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class DeviceState(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    device: str
    time: dt.datetime
    temperature: int
    battery_soc: int
    ipaddr: Optional[str] = None


class DB:
    """
    Database management use SQLModel.

    Second generation.
    """

    def __init__(self, filename: str = "device-data.db") -> None:
        "Constructor."

        self._engine = None

        self.filename = filename

    @property
    def filename(self) -> str:
        """
        Database filename.

        Returns:
            str: Filename.
        """

        return self._filename

    @filename.setter
    def filename(self, filename: str) -> None:
        """
        Set database filename.

        Args:
            filename (str): Filename.
        """
        if not isinstance(filename, str):
            raise TypeError(f"filename must be a string, not {type(filename)}")

        self._filename = filename
        self._engine = create_engine(f"sqlite:///{filename}")  # , echo=True)

        # This only creates the table if it doesn't exist.
        SQLModel.metadata.create_all(self._engine)

        self._session = Session(self._engine)

    def store(self, data: Union[DeviceState, List[DeviceState]]) -> None:
        """
        Store DeviceState data in database.

        Args:
            data (Union[DeviceState, List[DeviceState]]): DeviceState or list of DeviceState objects.
        """

        if isinstance(data, DeviceState):
            data = [data]

        for d in data:
            self._session.add(d)

        self._session.commit()

    @property
    def devices(self) -> list:
        """
        List of devices in database.

        Returns:
            list: List of device names in database.
        """

        # Get list of devices from database
        stmt = select(DeviceState.device).distinct()
        res = self._session.exec(stmt)

        return res.all()

    def device_latest(self, device: str) -> DeviceState:
        if device not in self.devices:
            logger.error(f'device "{device}" not in database')
            return None
        from sqlalchemy import func

        stmt = select(func.max(DeviceState.id)).where(DeviceState.device == device)
        id = self._session.exec(stmt).one()

        stmt = select(DeviceState).where(DeviceState.id == id)
        data = self._session.exec(stmt).one()

        return data

    def device_all(self, device: str) -> pd.DataFrame:
        """
        Returns all data in database for device as a pandas DataFrame.

        Returns:
            pd.DataFrame: All data in database.
        """

        if device not in self.devices:
            logger.error(f'device "{device}" not in database')
            return None

        stmt = select(DeviceState).where(DeviceState.device == device)
        res = self._session.exec(stmt)

        records = [x.dict() for x in res.all()]
        df = pd.DataFrame.from_records(records)

        return df

    def data_all(self) -> pd.DataFrame:
        """
        Returns all data in database as a pandas DataFrame.

        Returns:
            pd.DataFrame: All data in database.
        """

        stmt = select(DeviceState)
        res = self._session.exec(stmt)

        records = [x.dict() for x in res.all()]
        df = pd.DataFrame.from_records(records)

        return df


if __name__ == "__main__":
    # Test code
    db = DB()

    s1 = DeviceState(
        device="kitchen", time=dt.datetime.now(), temperature=1, battery_soc=1
    )
    s2 = DeviceState(
        device="kitchen",
        time=dt.datetime.now() + dt.timedelta(seconds=3),
        temperature=2,
        battery_soc=3,
    )
    s3 = DeviceState(
        device="home-office",
        time=dt.datetime.now() + dt.timedelta(seconds=7),
        temperature=4,
        battery_soc=5,
    )

    db.store(s1)
    db.store([s2, s3])
    dev = db.devices
    print(dev)
    print(db.device_latest("kitchen"))
