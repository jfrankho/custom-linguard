from logging import warning
from random import randint
from typing import Dict, Any

from schedule import repeat, every

from core.config.traffic_config import config
from core.drivers.traffic_storage_driver import TrafficStorageDriver
from core.drivers.traffic_storage_driver_json import TrafficStorageDriverJson
from core.models import interfaces


def bytes_to_gb(number: int):
    return number/1024/1024/1024


def gb_to_bytes(number: int):
    return number*1024*1024*1024


@repeat(every(1).hours)
def __update_data__():
    if not config.enabled:
        warning("Traffic's data collection is disabled!")
        return
    config.driver.update_data()


def get_wireguard_traffic_mock() -> Dict[str, Any]:
    dct = {}
    for iface in interfaces.values():
        rx = 0
        tx = 0
        for peer in iface.peers.values():
            peer_rx = randint(1000, 9999999999)
            peer_tx = randint(1000, 9999999999)
            dct[peer.name] = {
                "rx": peer_rx,
                "tx": peer_tx
            }
            rx += peer_rx
            tx += peer_tx
        dct[iface.name] = {
            "rx": rx,
            "tx": tx
        }
    return dct


registered_drivers: Dict[str, TrafficStorageDriver] = {}


def register_driver(driver: TrafficStorageDriver):
    name = driver.get_name()
    if name not in registered_drivers.keys():
        registered_drivers[name] = driver


def unregister_driver(name: str):
    if name in registered_drivers.keys():
        del registered_drivers[name]


register_driver(TrafficStorageDriverJson())
