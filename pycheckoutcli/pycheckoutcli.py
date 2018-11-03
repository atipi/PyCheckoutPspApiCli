# -*- coding: utf-8 -*-

"""
Client module to communicate with Checkout PSP API with normal payment

Checkout Finland PSP API specification
https://checkoutfinland.github.io/psp-api/#/

"""

import logging
import requests
import hmac
import six

from datetime import datetime


class CheckoutCli(object):
    _is_test_mode = 0
    _base_api_end_point = None
    _merchant_id = None
    _secret_key = None
    _algorithm = "sha256"
    _accepted_api_type = ["Payments", "PaymentDetails", "Refund", "ListProviders"]

    logger = None

    def __init__(self, is_test_mode=0, merchant_id=None, secret_key=None):

        logging.basicConfig(
            level=logging.DEBUG,
        )
        self.set_logger()

        self._is_test_mode = is_test_mode

        if is_test_mode == 1:
            self._base_api_end_point = 'https://api.checkout.fi'

            self._merchant_id = "375917"
            self._secret_key = "SAIPPUAKAUPPIAS"

        else:
            self._base_api_end_point = 'https://api.checkout.fi'

            if merchant_id is None:
                raise KeyError("Missing merchant id")
            self._merchant_id = merchant_id

            if secret_key is None:
                raise KeyError("Missing secret key")

            self._secret_key = str(secret_key)

    def set_logger(self):
        """
        Set logger object.

        :return:
        """
        self.logger = logging.getLogger(__name__)

    def get_logger(self):
        """
        Get logger object.

        :return:
        """
        return self.logger

    def validate_trans_id_data(self, transaction_id=None):
        if transaction_id is None or transaction_id == "":
            raise ValueError("Undefined transaction id")
        return

    def get_post_url(self, api_type="Payments", transaction_id=None):
        post_url = None
        if api_type == "Payments":
            post_url = self._base_api_end_point + '/payments'
        elif api_type == "PaymentDetails":
            self.validate_trans_id_data(transaction_id=transaction_id)
            post_url = self._base_api_end_point + '/payments/' + transaction_id
        elif api_type == "Refund":
            self.validate_trans_id_data(transaction_id=transaction_id)
            post_url = self._base_api_end_point + '/payments/' + transaction_id + '/refund'
        elif api_type == "ListProviders":
            post_url = self._base_api_end_point + '/merchants/payment-providers'

        return post_url

    def get_req_header_dict(self, api_type="Payment", method="POST", request_id=None, trans_id=None, \
                            time_stamp_string=None):

        if api_type not in self._accepted_api_type:
            raise ValueError("Invalid value in api_type parameter")

        if api_type == "PaymentDetails" or api_type == "Refund":
            if trans_id is None:
                raise KeyError("Missing data to trans_id parameter")

        if time_stamp_string is None:
            #TODO: must include timezone
            time_stamp = datetime.now().strftime('%Y-%m-%dT%H%M%S')

        header_dict = {
            'checkout-account': self._merchant_id,
            'checkout-algorithm': self._algorithm,
            'checkout-method': method,
            'checkout-nonce': request_id,
            'checkout-timestamp': time_stamp,
        }

        if api_type == "PaymentDetails" or api_type == "Refund":
            header_dict["checkout-transaction-id"] = trans_id

        return header_dict

    def get_hash_sha256(self, **kwargs):
        """
        Calculate SHA256 digest string.

        :param kwargs: dictionary of parameters for caluclation
        :return digest_string: digest string
        """
        if kwargs is None or len(kwargs) == 0:
            raise KeyError("Expect input parameters")

        secret_key = str(self._secret_key)
        self.logger.debug("Secret key: {}".format(secret_key))

        # - need to sort key alphabetically
        header_dict = sorted(kwargs["headers"])

        # some API will have body content
        body = kwargs.get("body", None)

        items = []
        for key in sorted(header_dict):
            self.logger.debug("Key={}, Value={}".format(key, header_dict[key]))
            # concate data to following format: key + ':' + value of headers dictionary
            temp_string = key + ':' + header_dict[key]
            items.append(str(temp_string))

        if body is not None:
            items.append(body)

        plain_text = "\n".join(map(str, items))
        if body is None:
            plain_text += "\n"
        self.logger.debug("Plain text={}".format(plain_text))

        if sys.version_info < (3, 0):
            # plain_text.decode('utf-8')
            message_bytes = bytes(plain_text)
            secret_bytes = bytes(secret_key)
        else:
            message_bytes = bytes(plain_text, 'utf-8')
            secret_bytes = bytes(secret_key, 'utf-8')

        hash_string = hmac.new(secret_bytes, message_bytes, hashlib.sha256)

        # to lowercase hexits
        digest_string = hash_string.hexdigest()
        self.logger.debug("Digest string={}".format(digest_string))

        return str(digest_string)

    def send_request(self, send_method='POST', _api_post_url=None, req_input=None, **headers):
        """
        Send a request to Checkout.

        :param send_method: type of request method. Possible value are 'POST' and 'GET', 'POST' is default value.
        :param _api_post_url: string of post URL
        :param req_input: request input data
        :param headers: dictionary of header data
        :return res_obj: response object
        """
        if _api_post_url is None or _api_post_url == '':
            raise ValueError("Need post URL data")

        if headers is None:
            headers = {
                # 'Content-type': 'application/x-www-form-urlencoded;charset=utf-8',
                'Content-Encoding': 'utf-8'
            }

        if send_method == 'POST':
            if req_input is None:
                res_obj = requests.post(_api_post_url, headers=headers)
            else:
                res_obj = requests.post(_api_post_url, data=req_input, headers=headers)

        else:
            if req_input is None:
                res_obj = requests.get(_api_post_url, headers=headers)
            else:
                res_obj = requests.get(_api_post_url, headers=headers, data=req_input, params=req_input)

        # self.logger.debug("Request headers={}".format(res_obj.request.headers))

        # Response data object is in 'res_obj' variable
        res_status_code = res_obj.status_code
        self.logger.debug("Response status code={}".format(res_status_code))
        # self.logger.debug("Response content={}".format(res_obj.content))

        if res_status_code != 200 and res_status_code != 201:
            error_text = res_obj.content
            self.logger.error("Unexpected response text={}".format(error_text))
            raise Exception(error_text)

        return res_obj

    def get_create_payment_keys(self):
        data = ['stamp', 'reference', 'amount', 'currency', 'language', 'items', 'customer', 'deliveryAddress',\
                'invoicingAddress', 'redirectUrls', 'callbackUrls']
        return data

    def validate_create_payment_input(self, **kwargs):
        if kwargs is None or len(kwargs) == 0:
            raise KeyError("Expect input parameters")

        keyList = self.get_create_payment_keys()
        for key in keyList:
            value = kwargs.get(key, None)
            if value is None:
                error_msg = "Missing " + key + " parameter"
                raise ValueError(error_msg)

        return

    def validate_data_dict(self, key_dict=None, data_dict=None):
        if key_dict is None:
            raise KeyError("Missing key mapping data in key_dict parameter")

        if data_dict is None:
            raise KeyError("Missing value in data_dict parameter")

        for key in key_dict:
            if key_dict[key] is True:
                if key not in data_dict:
                    error_msg = "Missing mandatory key: " + key
                    raise KeyError(error_msg)

                value = data_dict[key]
                if value is None:
                    error_msg = "Invalid value in " + key + " parameter"
                    raise KeyError(error_msg)
        return

    def validate_customer_key_value_in_create_payment(self, customer_dict=None):
        if customer_dict is None:
            raise KeyError("Missing customer_dict parameter")

        keySet = {
            "firstName": True,
            "lastName": True,
            "email": True,
            "phone": False,
            "vatId": False
        }

        self.validate_data_dict(key_dict=keySet, data_dict=customer_dict)

        return

    def validate_language_code2(self, language_code=None):
        if language_code is None:
            raise KeyError("Missing language_code parameter")

        if not isinstance(language_code, six.string_types):
            raise ValueError("Expect string data type for language parameter")

        code_length = len(language_code)
        if code_length > 2:
            raise ValueError("Invalid language code value length. Expected 2 letters of language code")

        # Support only FI, SV, and EN
        if language_code != "FI" and language_code != "SV" and language_code != "EN":
            raise ValueError("Invalid value. Support only FI, SV and EN")

        return

    def validate_address_value_in_create_payment(self, data_dict=None):
        if data_dict is None:
            raise KeyError("Missing data_dict parameter")

        keySet = {
            "streetAddress": True,
            "postalCode": True,
            "city": True,
            "county": False,
            "country": True
        }

        self.validate_data_dict(key_dict=keySet, data_dict=data_dict)

        # Validate country code
        if not isinstance(value, six.string_types):
            raise ValueError("Expect string data type for country parameter")

        country_code_length = len(data_dict["country"])
        if country_code_length > 2:
            raise ValueError("Invalid country code value length. Expected 2 letters of country code")

        # Convert to upper case
        data_dict["country"].upper()

        return

    def validate_int_value(self, key=None, value=None):

        if not isinstance(value, int):
            error_msg = "Expect int value in " + key + " parameter"
            raise ValueError(error_msg)
        return

    def validate_item_data_in_create_payment(self, data_dict=None):
        if data_dict is None:
            raise KeyError("Missing data_dict parameter")

        keySet = {
            "unitPrice": True,
            "units": True,
            "vatPercentage": True,
            "productCode": True,
            "deliveryDate": True,
            "description": False,
            "category": False,
            "stamp": False,
            "reference": False,
            "merchant": False,
            "commission": False
        }

        self.validate_data_dict(key_dict=keySet, data_dict=data_dict)

        self.validate_int_value(key="unitPrice", value=data_dict["unitPrice"])

        self.validate_int_value(key="units", value=data_dict["units"])

        self.validate_int_value(key="vatPercentage", value=data_dict["vatPercentage"])

        return

    def validate_callback_urls_data(self, data_dict=None):
        if data_dict is None:
            raise KeyError("Missing data_dict parameter")

        keySet = {
            "success": True,
            "cancel": True
        }

        self.validate_data_dict(key_dict=keySet, data_dict=data_dict)

        # TODO: check that data starts with "https://"

        return

    def get_test_req_create_payment_data(self):
        data = {
            "stamp": 29858472952, # order id
            "reference": 9187445,
            "amount": 1590,
            "currency": "EUR",
            "language": "FI",
            "items": [
                {
                    "unitPrice": 1590,
                    "units": 1,
                    "vatPercentage": 24,
                    "productCode": "#927502759",
                    "deliveryDate": "2018-03-07",
                    "description": "Cat ladder",
                    "category": "shoe",
                    "merchant": 375917,
                    "stamp": 29858472952,
                    "reference": 9187445,
                    "commission": {
                        "merchant": "string",
                        "amount": 0
                    }
                }
            ],
            "customer": {
                "email": "john.doe@example.org",
                "firstName": "John",
                "lastName": "Doe",
                "phone": 358501234567,
                "vatId": "FI02454583"
            },
            "deliveryAddress": {
                "streetAddress": "Fake street 123",
                "postalCode": "00100",
                "city": "Luleå",
                "county": "Norrbotten",
                "country": "Sweden"
            },
            "invoicingAddress": {
                "streetAddress": "Fake street 123",
                "postalCode": "00100",
                "city": "Luleå",
                "county": "Norrbotten",
                "country": "Sweden"
            },
            "redirectUrls": {
                "success": "https://ecom.example.org/success",
                "cancel": "https://ecom.example.org/cancel"
            },
            "callbackUrls": {
                "success": "https://ecom.example.org/success",
                "cancel": "https://ecom.example.org/cancel"
            }
        }
        return data

    def create_payment(self, request_id=None, input_data_dict=None, time_stamp_string=None):
        if request_id is None:
            raise KeyError("Missing unique request id value in request_id parameter")

        if self._is_test_mode == 1:
            if input_data_dict is None:
                # get test data set
                input_data_dict = self.get_test_req_create_payment_data()
        else:
            if input_data_dict is None:
                raise KeyError("Missing input request parameters")

        # Start input data validation
        self.validate_create_payment_input(**input_data_dict)

        currency = input_data_dict["currency"]
        if currency != "EUR":
            raise ValueError("Invalid currency value. Support only EUR.")

        language = input_data_dict["language"]
        self.validate_language_code2(language_code=language)
        input_data_dict["language"].upper()

        customer_dict = input_data_dict["customer"]
        if type(customer_dict) is dict:
            pass
        else:
            raise ValueError("Invalid data type for customer key")

        self.validate_address_value_in_create_payment(data_dict=input_data_dict["invoicingAddress"])

        self.validate_address_value_in_create_payment(data_dict=input_data_dict["deliveryAddress"])

        self.validate_item_data_in_create_payment(data_dict=input_data_dict["items"])

        self.validate_callback_urls_data(data_dict=input_data_dict["redirectUrls"])

        self.validate_callback_urls_data(data_dict=input_data_dict["callbackUrls"])

        # Everything OK now can proceed sending data to Checkout
        post_url = self.get_post_url(api_type="Payments")

        headers_dict = self.get_req_header_dict(api_type="Payments", method="POST", request_id=request_id,\
                                                time_stamp_string=time_stamp_string)

        # Calculate HMAC
        hmac_dict = { "headers": headers_dict, "body": None }
        signature = self.get_hash_sha256(**hmac_dict)

        # Add HMAC to request header parameters
        headers_dict["signature"] = signature

        # set common settings in request header parameters
        headers_dict["Content-Type"] = 'application/json; charset=utf-8'
        headers_dict["Accept"] = 'application/json'

        # Do send a call
        res_obj = self.send_request(send_method="POST", _api_post_url=post_url, req_input=input_data_dict)

        return res_obj
