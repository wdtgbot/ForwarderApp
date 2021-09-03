import json
import logging
from forwarder.message import Message
from datetime import datetime
from getpass import getpass


class Forwarder:
    NEW_MESSAGE = "updateNewMessage"
    AUTHORIZATION = "updateAuthorizationState"
    ERROR = "error"

    def __init__(
        self, client, limit_chats, periodicity_fwd, rules_path, log_path
    ) -> None:
        self.logger = logging.getLogger(__name__)
        self.client = client
        self.rules_path = rules_path
        self.log_path = log_path
        self.periodicity_fwd = periodicity_fwd
        self.limit_chats = limit_chats

        # load rules file
        rules_file = open(self.rules_path)
        self.rules = json.load(rules_file)
        rules_file.close()

        # forwarder variables
        self.forwarded = 0
        self.messages = []
        self.start_update_time = 0

    def __str__(self) -> str:
        return (
            "{"
            + f"client: {self.client}, log_path: {self.log_path}, rules_path: {self.rules_path}, log_path: {self.log_path}, periodicity_fwd: {self.periodicity_fwd}, limit_chats: {self.limit_chats}"
            + "}"
        )

    def start(self):
        # start the client by sending request to it
        self.client.td_send({"@type": "getAuthorizationState", "@extra": 1.01234})

        # chrono
        self.start_update_time = datetime.now()
        try:
            # main events cycle
            while True:
                self.recently_added = False
                event = self.client.td_receive()

                if event:
                    # authenticate user
                    self.authenticate_user(event)

                    # handle new messages
                    self.new_message_update_handler(event)

                    # handler errors
                    self.error_update_handler(event)

                # process all messages
                self.process_message_queue()

        except KeyboardInterrupt:
            self.logger.info("Listening to messages stopped by user")

    def authenticate_user(self, event) -> None:
        # process authorization states
        if event["@type"] == self.AUTHORIZATION:
            auth_state = event["authorization_state"]

            # if client is closed, we need to destroy it and create new client
            if auth_state["@type"] == "authorizationStateClosed":
                self.logger.critical(event)
                raise ValueError(event)

            # set TDLib parameters
            # you MUST obtain your own api_id and api_hash at https://my.telegram.org
            # and use them in the setTdlibParameters call
            if auth_state["@type"] == "authorizationStateWaitTdlibParameters":
                self.client.td_send(
                    {
                        "@type": "setTdlibParameters",
                        "parameters": {
                            "database_directory": self.client.database_directory,
                            "use_file_database": self.client.use_file_database,
                            "use_secret_chats": self.client.use_secret_chats,
                            "api_id": self.client.api_id,
                            "api_hash": self.client.api_hash,
                            "system_language_code": self.client.system_language,
                            "device_model": self.client.device_model,
                            "application_version": self.client.app_version,
                            "enable_storage_optimizer": self.client.enable_storage_optimizer,
                        },
                    }
                )

            # set an encryption key for database to let know TDLib how to open the database
            if auth_state["@type"] == "authorizationStateWaitEncryptionKey":
                self.client.td_send(
                    {
                        "@type": "checkDatabaseEncryptionKey",
                        "encryption_key": "",
                    }
                )

            # enter phone number to log in
            if auth_state["@type"] == "authorizationStateWaitPhoneNumber":
                phone_number = input("Please enter your phone number: ")
                self.client.td_send(
                    {
                        "@type": "setAuthenticationPhoneNumber",
                        "phone_number": phone_number,
                    }
                )

            # wait for authorization code
            if auth_state["@type"] == "authorizationStateWaitCode":
                code = input("Please enter the authentication code you received: ")
                self.client.td_send({"@type": "checkAuthenticationCode", "code": code})

            # wait for first and last name for new users
            if auth_state["@type"] == "authorizationStateWaitRegistration":
                first_name = input("Please enter your first name: ")
                last_name = input("Please enter your last name: ")
                self.client.td_send(
                    {
                        "@type": "registerUser",
                        "first_name": first_name,
                        "last_name": last_name,
                    }
                )

            # wait for password if present
            if auth_state["@type"] == "authorizationStateWaitPassword":
                password = getpass("Please enter your password: ")
                self.client.td_send(
                    {
                        "@type": "checkAuthenticationPassword",
                        "password": password,
                    }
                )

            # user authenticated
            if auth_state["@type"] == "authorizationStateReady":
                # get all chats
                self.client.td_send({"@type": "getChats", "limit": self.limit_chats})
                self.logger.debug("User authorized")

    def new_message_update_handler(self, event):
        # handle incoming messages
        if event["@type"] == self.NEW_MESSAGE:
            message_update = event["message"]

            for rule in self.rules["forward"]:
                # if the message from chat_id is not from an accepted source
                if message_update["chat_id"] != rule["source"]:
                    continue
                message = Message(
                    message_update["id"],
                    message_update["chat_id"],
                    message_update["date"],
                    rule["id"],
                )

                if self.client.group_messages:
                    # append the message to the queue
                    self.messages.append(message)
                    self.logger.debug(f"Message {message}, appended to the queue")
                    self.recently_added = True
                else:
                    self.forward_message(message)

    def error_update_handler(self, event):
        if event["@type"] == self.ERROR:
            # log the error
            self.logger.error(event)

    def forward_message(self, message):
        for rule in self.rules["forward"]:
            if message.rule_id == rule["id"]:
                # variables
                destination_ids = rule["destination"]
                source_id = rule["source"]
                message_id = message.message_id
                options = rule["options"]
                send_copy = rule["send_copy"]
                remove_caption = rule["remove_caption"]
                for chat_id in destination_ids:
                    # forward messages
                    self.client.forward_message(
                        chat_id,
                        source_id,
                        message_id,
                        options,
                        send_copy,
                        remove_caption,
                    )
                    # log action
                    self.logger.info(f"Message forwarding has been sent to the API")
                    print(f"Message forwarded: {message}")

    def process_message_queue(self):
        # proccess queue messages
        self.now = datetime.now()
        self.difference_seconds = int(
            (self.now - self.start_update_time).total_seconds()
        )

        if self.difference_seconds % self.periodicity_fwd == 0:
            # only execute this once every x seconds
            if self.forwarded < self.difference_seconds:
                # message added recently, skip to next iteration
                if not self.recently_added:
                    # there are messages to proccess
                    if self.messages:
                        self.logger.debug("Processing message queue")

                        # proccess stored messages
                        self.proccess_messages()

                        # clear queue of messages
                        self.messages.clear()
                        self.logger.debug("Message queue processed and cleared")

                    # updates forwarded state
                    self.forwarded = self.difference_seconds

    # forward stored messages in queue
    def proccess_messages(self) -> None:
        grouped_messages = self.group_message_id(self.messages)
        self.logger.debug("Message/s grouped by rule_id")

        for message in grouped_messages:
            self.forward_message(message)

    # group message_id by rule_id
    def group_message_id(self, messages) -> list:
        result = []
        for message in messages:
            if not result:
                result.append(message)
            else:
                for index, row in enumerate(result):
                    if row.rule_id == message.rule_id:
                        row.message_id.extend(message.message_id)
                        break
                    else:
                        # if is the last index
                        if index == len(result) - 1:
                            result.append(message)
                            break
        return result
