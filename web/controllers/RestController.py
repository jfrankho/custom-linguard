import http
import io
from http.client import NO_CONTENT, INTERNAL_SERVER_ERROR
from logging import debug

from flask import Response, send_file, url_for, redirect, abort
from flask_login import login_user

from core.config.linguard_config import config as linguard_config, LinguardConfig
from core.config.logger_config import config as logger_config, LoggerConfig
from core.config.web_config import config as web_config, WebConfig
from core.config_manager import config_manager
from core.exceptions import WireguardError
from core.models import Interface, Peer, interfaces
from system_utils import log_exception, str_to_list
from web.controllers.ViewController import ViewController
from web.models import users, User


class RestController:

    def __init__(self, uuid: str = ""):
        self.uuid = uuid

    @staticmethod
    def __save_iface__(iface: Interface, form):
        iface.edit(name=form.name.data, description=form.description.data,
                   gw_iface=form.gateway.data, ipv4_address=form.ipv4.data, port=form.port.data,
                   auto=form.auto.data, on_up=str_to_list(form.on_up.data),
                   on_down=str_to_list(form.on_down.data))
        config_manager.save()

    def apply_iface(self, iface: Interface, form):
        self.__save_iface__(iface, form)
        iface.apply()

    @staticmethod
    def add_iface(form):
        on_up = str_to_list(form.on_up.data)
        on_down = str_to_list(form.on_down.data)
        iface = Interface(name=form.name.data, description=form.description.data, gw_iface=form.gateway.data,
                          ipv4_address=form.ipv4.data, listen_port=form.port.data, auto=form.auto.data, on_up=on_up,
                          on_down=on_down)
        interfaces[iface.uuid] = iface
        interfaces.sort()
        config_manager.save()

    def remove_iface(self) -> Response:
        try:
            interfaces[self.uuid].remove()
            config_manager.save()
            return Response(status=NO_CONTENT)
        except WireguardError as e:
            log_exception(e)
            return Response(str(e), status=e.http_code)
        except Exception as e:
            log_exception(e)
            return Response(str(e), status=INTERNAL_SERVER_ERROR)

    @staticmethod
    def add_peer(form) -> Peer:
        iface = interfaces.get_value_by_attr("name", form.interface.data)
        peer = Peer(name=form.name.data, description=form.description.data,
                    interface=iface, ipv4_address=form.ipv4.data,
                    dns1=form.dns1.data, dns2=form.dns2.data, nat=form.nat.data)
        iface.add_peer(peer)
        config_manager.save()
        return peer

    @staticmethod
    def remove_peer(peer: Peer) -> Response:
        try:
            peer.remove()
            config_manager.save()
            return Response(status=NO_CONTENT)
        except Exception as e:
            log_exception(e)
            return Response(str(e), status=INTERNAL_SERVER_ERROR)

    @staticmethod
    def save_peer(peer: Peer, form):
        iface = interfaces.get_value_by_attr("name", form.interface.data)
        peer.edit(name=form.name.data, description=form.description.data, interface=iface,
                  ipv4_address=form.ipv4.data, nat=form.nat.data, dns1=form.dns1.data, dns2=form.dns2.data)
        config_manager.save()

    def download_peer(self, peer: Peer) -> Response:
        try:
            conf = peer.generate_conf()
            return self.send_text_as_file(filename=f"{peer.name}.conf", text=conf)
        except WireguardError as e:
            log_exception(e)
            return Response(str(e), status=e.http_code)
        except Exception as e:
            log_exception(e)
            return Response(str(e), status=INTERNAL_SERVER_ERROR)

    def download_iface(self, iface: Interface) -> Response:
        try:
            conf = iface.generate_conf()
            return self.send_text_as_file(filename=f"{iface.name}.conf", text=conf)
        except Exception as e:
            log_exception(e)
            return Response(str(e), status=INTERNAL_SERVER_ERROR)

    @staticmethod
    def send_text_as_file(filename: str, text: str):
        proxy = io.StringIO()
        proxy.writelines(text)
        # Creating the byteIO object from the StringIO Object
        mem = io.BytesIO()
        mem.write(proxy.getvalue().encode())
        # seeking was necessary. Python 3.5.2, Flask 0.12.2
        mem.seek(0)
        proxy.close()
        return send_file(mem, as_attachment=True, attachment_filename=filename, mimetype="text/plain")

    @staticmethod
    def save_settings(form):
        sample_logger = LoggerConfig()

        logger_config.logfile = form.log_file.data or sample_logger.logfile
        logger_config.overwrite = form.log_overwrite.data == "Yes" or sample_logger.overwrite
        logger_config.level = form.log_level.data or sample_logger.level

        sample_web = WebConfig()

        web_config.host = form.web_adapter.data or sample_web.host
        web_config.bindport = form.web_port.data or sample_web.bindport
        web_config.login_attempts = form.web_login_attempts.data or sample_web.login_attempts
        web_config.secret_key = form.web_secret_key.data or sample_web.secret_key
        web_config.credentials_file = form.web_credentials_file.data or sample_web.credentials_file

        sample_linguard = LinguardConfig()

        linguard_config.endpoint = form.app_endpoint.data or sample_linguard.endpoint
        linguard_config.wg_bin = form.app_wg_bin.data or sample_linguard.wg_bin
        linguard_config.wg_quick_bin = form.app_wg_quick_bin.data or sample_linguard.wg_quick_bin
        linguard_config.iptables_bin = form.app_iptables_bin.data or sample_linguard.iptables_bin
        linguard_config.interfaces_folder = form.app_interfaces_folder.data or sample_linguard.interfaces_folder

        config_manager.save()

    @staticmethod
    def signup(form):
        if not form.validate():
            context = {
                "title": "Create admin account",
                "form": form
            }
            return ViewController("web/signup.html", **context).load()
        debug(f"Signing up user '{form.username.data}'...")
        u = User(form.username.data)
        u.password = form.password.data
        users[u.id] = u
        users.save(web_config.credentials_file, web_config.secret_key)
        debug(f"Logging in user '{u.id}'...")

        if u.login(form.password.data) and login_user(u):
            return redirect(form.next.data or url_for("router.index"))
        abort(http.HTTPStatus.INTERNAL_SERVER_ERROR)
