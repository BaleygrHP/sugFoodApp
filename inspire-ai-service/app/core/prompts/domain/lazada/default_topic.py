from enum import StrEnum


class DefaultTopic(StrEnum):
    LAZADA_ORDER_INFO = "lazada:order_information"
    LAZADA_ORDER_CANCELLATION = "lazada:order_cancelation"
    LAZADA_PRODUCT_CONSULTATION = "lazada:product_consultation"
    LAZADA_HUMAN_SUPPORT = "lazada:human_support"
