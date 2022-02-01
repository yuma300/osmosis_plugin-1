import re
from decimal import Decimal
from senkalib.chain.transaction import Transaction
from senkalib.caaj_plugin import CaajPlugin
from senkalib.caaj_journal import CaajJournal

MEGA = 10**6

EXA = 10**18


class OsmosisPlugin(CaajPlugin):
    chain = "osmosis"

    @classmethod
    def can_handle(cls, transaction: Transaction) -> bool:
        chain_type = transaction.get_transaction()["header"]["chain_id"]
        if "osmosis" in chain_type:
            return True
        else:

            return False

    @classmethod
    def get_caajs(cls, address: str, transaction: Transaction) -> CaajJournal:
        if transaction.get_transaction()["data"]["code"] == 0:
            transaction_type = transaction.get_transaction()["data"]["tx"]["body"][
                "messages"
            ][0]["@type"].split(".")[-1]

            if transaction_type in [
                "MsgSwapExactAmountIn",
                "MsgJoinSwapExternAmountIn",
                "MsgUndelegate",
            ]:
                caaj_main = OsmosisPlugin.__get_caaj_swap(transaction)

            elif transaction_type in ["MsgLockTokens", "MsgTransfer", "MsgSend"]:
                caaj_main = OsmosisPlugin.__get_caaj_send(transaction)

            elif transaction_type == "MsgJoinPool":
                caaj_main = OsmosisPlugin.__get_caaj_join_pool(transaction)

            elif transaction_type == "MsgExitPool":
                caaj_main = OsmosisPlugin.__get_caaj_exit_pool(transaction)

            elif transaction_type == "MsgDelegate":
                caaj_main = OsmosisPlugin.__get_caaj_delegate(transaction, address)

            elif transaction_type in [
                "MsgBeginUnlocking",
                "MsgWithdrawDelegatorReward",
                "MsgVote",
                "MsgUnlockPeriodLock",
                "MsgBeginRedelegate",
            ]:
                caaj_main = []

            if transaction.get_transaction_fee() != 0 and caaj_main:
                caaj_fee = OsmosisPlugin.__get_caaj_fee(transaction, address)
                caaj = caaj_main + caaj_fee
                return caaj

            elif transaction.get_transaction_fee() != 0 and not caaj_main:
                caaj_fee = OsmosisPlugin.__get_caaj_fee(transaction, address)
                return caaj_fee

            elif transaction.get_transaction_fee() == 0 and caaj_main:
                print(caaj_main)
                return caaj_main

            else:
                return []
        else:
            return []

    @classmethod
    def __get_caaj_swap(cls, transaction: Transaction) -> CaajJournal:
        caaj = []
        attributes_list = OsmosisPlugin.__get_attributes_list(transaction, "transfer")
        for _, attribute in enumerate(attributes_list):
            senders = OsmosisPlugin.__get_attribute_data(attribute, "sender")
            recipients = OsmosisPlugin.__get_attribute_data(attribute, "recipient")
            amounts = OsmosisPlugin.__get_attribute_data(attribute, "amount")
            credit_to = recipients[0]["value"]
            credit_from = senders[0]["value"]
            credit_token_amount = str(
                OsmosisPlugin.__get_token_amount(amounts[0]["value"])
            )
            credit_token_name = OsmosisPlugin.__get_token_name(amounts[0]["value"])
            credit_amount = {credit_token_name: credit_token_amount}

            debit_to = recipients[1]["value"]
            debit_from = senders[1]["value"]
            debit_token_amount = str(
                OsmosisPlugin.__get_token_amount(amounts[1]["value"])
            )
            debit_token_name = OsmosisPlugin.__get_token_name(amounts[1]["value"])
            debit_amount = {debit_token_name: debit_token_amount}

            debit_title = "SPOT"
            credit_title = "SPOT"

            caaj_meta = CaajJournal.get_caaj_meta(
                transaction.get_timestamp(), transaction.transaction_id, "osmosis swap"
            )
            caaj_destination = CaajJournal.get_caaj_destination(
                debit_from, debit_to, credit_from, credit_to
            )
            caaj_value = CaajJournal.get_caaj_value(
                debit_title, debit_amount, credit_title, credit_amount
            )

            caaj_main = dict(**caaj_meta, **caaj_destination, **caaj_value)
            caaj.append(caaj_main)

        return caaj

    @classmethod
    def __get_caaj_send(cls, transaction: Transaction) -> CaajJournal:
        caaj = []

        attributes_list = OsmosisPlugin.__get_attributes_list(transaction, "transfer")
        for _, attribute in enumerate(attributes_list):
            senders = OsmosisPlugin.__get_attribute_data(attribute, "sender")
            recipients = OsmosisPlugin.__get_attribute_data(attribute, "recipient")
            amounts = OsmosisPlugin.__get_attribute_data(attribute, "amount")

            credit_from = senders[0]["value"]
            credit_to = recipients[0]["value"]
            debit_to = senders[0]["value"]
            debit_from = recipients[0]["value"]

            credit_name = OsmosisPlugin.__get_token_name(amounts[0]["value"])
            debit_name = OsmosisPlugin.__get_token_name(amounts[0]["value"])

            credit_amount = {
                credit_name: str(OsmosisPlugin.__get_token_amount(amounts[0]["value"]))
            }
            debit_amount = {
                debit_name: str(OsmosisPlugin.__get_token_amount(amounts[0]["value"]))
            }

            debit_title = "RECEIVE"
            credit_title = "SPOT"

            caaj_meta = CaajJournal.get_caaj_meta(
                transaction.get_timestamp(),
                transaction.transaction_id,
                "osmosis remove liquidity",
            )

            caaj_destination = CaajJournal.get_caaj_destination(
                debit_from, debit_to, credit_from, credit_to
            )
            caaj_value = CaajJournal.get_caaj_value(
                debit_title, debit_amount, credit_title, credit_amount
            )

            caaj_main = dict(**caaj_meta, **caaj_destination, **caaj_value)
            caaj.append(caaj_main)

        return caaj

    @classmethod
    def __get_caaj_join_pool(cls, transaction: Transaction) -> CaajJournal:
        caaj = []

        attributes_list = OsmosisPlugin.__get_attributes_list(transaction, "transfer")
        for _, attribute in enumerate(attributes_list):
            senders = OsmosisPlugin.__get_attribute_data(attribute, "sender")
            recipients = OsmosisPlugin.__get_attribute_data(attribute, "recipient")
            amounts = OsmosisPlugin.__get_attribute_data(attribute, "amount")

            credit_from = senders[0]["value"]
            credit_to = recipients[0]["value"]
            debit_from = senders[1]["value"]
            debit_to = recipients[1]["value"]

            credit_amounts = amounts[0]["value"].split(",")
            credit_amount_0 = str(OsmosisPlugin.__get_token_amount(credit_amounts[0]))
            credit_amount_1 = str(OsmosisPlugin.__get_token_amount(credit_amounts[1]))
            credit_name_0 = OsmosisPlugin.__get_token_name(credit_amounts[0])
            credit_name_1 = OsmosisPlugin.__get_token_name(credit_amounts[1])
            credit_amount = {
                credit_name_0: credit_amount_0,
                credit_name_1: credit_amount_1,
            }

            debit_amount = {
                OsmosisPlugin.__get_token_name(amounts[1]["value"]): str(
                    OsmosisPlugin.__get_token_amount(amounts[1]["value"])
                )
            }

            debit_title = "LIQUIDITY"
            credit_title = "SPOT"

            caaj_meta = CaajJournal.get_caaj_meta(
                transaction.get_timestamp(),
                transaction.transaction_id,
                "osmosis add liquidity",
            )

            caaj_destination = CaajJournal.get_caaj_destination(
                debit_from, debit_to, credit_from, credit_to
            )
            caaj_value = CaajJournal.get_caaj_value(
                debit_title, debit_amount, credit_title, credit_amount
            )

            caaj_main = dict(**caaj_meta, **caaj_destination, **caaj_value)

            caaj.append(caaj_main)

        return caaj

    @classmethod
    def __get_caaj_exit_pool(cls, transaction: Transaction) -> CaajJournal:
        caaj = []

        attributes_list = OsmosisPlugin.__get_attributes_list(transaction, "transfer")
        for _, attribute in enumerate(attributes_list):
            senders = OsmosisPlugin.__get_attribute_data(attribute, "sender")
            recipients = OsmosisPlugin.__get_attribute_data(attribute, "recipient")
            amounts = OsmosisPlugin.__get_attribute_data(attribute, "amount")

            credit_from = senders[1]["value"]
            debit_to = recipients[0]["value"]
            credit_to = recipients[1]["value"]
            debit_from = senders[0]["value"]

            debit_amounts = amounts[0]["value"].split(",")

            debit_amount_0 = str(OsmosisPlugin.__get_token_amount(debit_amounts[0]))
            debit_amount_1 = str(OsmosisPlugin.__get_token_amount(debit_amounts[1]))

            credit_amount = str(OsmosisPlugin.__get_token_amount(amounts[1]["value"]))

            debit_name_0 = OsmosisPlugin.__get_token_name(debit_amounts[0])
            debit_name_1 = OsmosisPlugin.__get_token_name(debit_amounts[1])
            credit_name = OsmosisPlugin.__get_token_name(amounts[1]["value"])

            debit_amount = {debit_name_0: debit_amount_0, debit_name_1: debit_amount_1}
            credit_amount = {credit_name: credit_amount}

            debit_title = "SPOT"
            credit_title = "LIQUIDITY"

            caaj_meta = CaajJournal.get_caaj_meta(
                transaction.get_timestamp(),
                transaction.transaction_id,
                "osmosis remove liquidity",
            )

            caaj_destination = CaajJournal.get_caaj_destination(
                debit_from, debit_to, credit_from, credit_to
            )
            caaj_value = CaajJournal.get_caaj_value(
                debit_title, debit_amount, credit_title, credit_amount
            )

            caaj_main = dict(**caaj_meta, **caaj_destination, **caaj_value)

            caaj.append(caaj_main)

        return caaj

    @classmethod
    def __get_caaj_delegate(cls, transaction: Transaction, address: str) -> CaajJournal:
        caaj = []

        attributes_list_delegate = OsmosisPlugin.__get_attributes_list(
            transaction, "delegate"
        )
        for _, attribute in enumerate(attributes_list_delegate):
            recipients = OsmosisPlugin.__get_attribute_data(attribute, "validator")
            amounts = OsmosisPlugin.__get_attribute_data(attribute, "amount")

            credit_from = address
            credit_to = recipients[0]["value"]
            debit_to = address
            debit_from = recipients[0]["value"]

            credit_amount = {
                "osmo": str(OsmosisPlugin.__get_token_amount(amounts[0]["value"]))
            }
            debit_amount = {
                "osmo": str(OsmosisPlugin.__get_token_amount(amounts[0]["value"]))
            }

            debit_title = "DELEGATE"
            credit_title = "SPOT"

            caaj_meta = CaajJournal.get_caaj_meta(
                transaction.get_timestamp(),
                transaction.transaction_id,
                "osmosis remove liquidity",
            )
            caaj_destination = CaajJournal.get_caaj_destination(
                debit_from, debit_to, credit_from, credit_to
            )
            caaj_value = CaajJournal.get_caaj_value(
                debit_title, debit_amount, credit_title, credit_amount
            )

            caaj_main = dict(**caaj_meta, **caaj_destination, **caaj_value)
            caaj.append(caaj_main)

        attributes_list_transfer = OsmosisPlugin.__get_attributes_list(
            transaction, "transfer"
        )
        if len(attributes_list_transfer) > 0:
            caaj_send = OsmosisPlugin.__get_caaj_send(transaction)

            caaj.extend(caaj_send)
        return caaj

    @classmethod
    def __get_caaj_fee(cls, transaction: Transaction, user_address: str) -> CaajJournal:
        debit_from = "0x0000000000000000000000000000000000000000"
        debit_to = user_address
        credit_from = user_address
        credit_to = "0x0000000000000000000000000000000000000000"

        debit_title = "FEE"
        credit_title = "SPOT"

        amount = {"OSMO": str(transaction.get_transaction_fee() / Decimal(MEGA))}

        caaj_meta = CaajJournal.get_caaj_meta(
            transaction.get_timestamp(),
            transaction.transaction_id,
            "osmosis transaction fee",
        )
        caaj_destination = CaajJournal.get_caaj_destination(
            debit_from, debit_to, credit_from, credit_to
        )
        caaj_value = CaajJournal.get_caaj_value(
            debit_title, amount, credit_title, amount
        )

        caaj = dict(**caaj_meta, **caaj_destination, **caaj_value)

        return [caaj]

    @classmethod
    def __get_attributes_list(cls, transaction: Transaction, event_type: str) -> dict:
        logs = transaction.get_transaction()["data"]["logs"]
        events_list = []
        for i, _ in enumerate(logs):
            events = list(
                filter(lambda event: event["type"] == event_type, logs[i]["events"])
            )
            if len(events) > 0:
                events_list.append(*events)

        attributes_list = list(map(lambda event: event["attributes"], events_list))

        return attributes_list

    @classmethod
    def __get_attribute_data(cls, attribute: dict, attribute_key: str) -> list:
        attribute_data = list(
            filter(lambda attribute: attribute["key"] == attribute_key, attribute)
        )

        return attribute_data

    @classmethod
    def __get_token_name(cls, value: str) -> str:
        token_name = value[re.search(r"\d+", value).end() :]
        if token_name == "uosmo" or token_name == "":
            token_name = "osmo"
        elif token_name == "uion":
            token_name = "ion"

        return token_name

    @classmethod
    def __get_token_amount(cls, value: str) -> int:

        if "pool" in value:
            token_amount = str(Decimal(re.search(r"\d+", value).group()) / Decimal(EXA))

        else:
            token_amount = str(
                Decimal(re.search(r"\d+", value).group()) / Decimal(MEGA)
            )
        return token_amount
