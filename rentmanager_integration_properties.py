import requests
import logging
import json

from rentmanager_integration_consts import *

class RentManagerIntegration():

    def __init__(self):

        self._access_token = None
    
    def get_token(self):

        # Authenticate to fetch token using username and password
        authentication_payload = json.dumps({
            "Username": RENTMANAGER_API_USERNAME,
            "Password": RENTMANAGER_API_PASSWORD
        })

        authentication_headers = {
        'Content-Type': 'application/json'
        }

        authentication_endpoint = "{}{}".format(RENTMANAGER_BASE_URL, '/Authentication/AuthorizeUser')

        ret_val, _access_token = connector._make_rest_call(url=authentication_endpoint, data=authentication_payload,
                    headers=authentication_headers, method="post")

        return ret_val, _access_token

    def _make_rest_call(self, url=None, params=None, headers=None, data=None, method="get"):

        try:
            request_func = getattr(requests, method)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return False, error_message

        try:
            response = request_func(url, params=params, headers=headers, data=data)
        except Exception as e:
            error_message = self._get_error_message_from_exception(e)
            return False, error_message

        return self._process_response(response)

    def _process_response(self, r):

        # Process a json response
        if 'json' in r.headers.get('Content-Type', ''):
            return self._process_json_response(r)

        message = "Can't process response from server. Status Code: {0} Data from server: {1}".format(
                r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

        return False, message

    def _process_json_response(self, r):

        # Try a json parse
        try:
            resp_json = r.json()
        except Exception as e:
            logger.debug('Cannot parse JSON')
            return False, "Unable to parse response as JSON"

        if (200 <= r.status_code < 205):
            return True, resp_json

        error_info = resp_json if type(resp_json) is str else resp_json.get('error', {})
        try:
            if error_info.get('code') and error_info.get('message') and type(resp_json):
                error_details = {
                    'message': error_info.get('code'),
                    'detail': error_info.get('message')
                }
                return False, "Error from server, Status Code: {0} data returned: {1}".format(r.status_code, error_details)
            else:
                return False, "Error from server, Status Code: {0} data returned: {1}".format(r.status_code, r.text.replace('{', '{{').replace('}', '}}'))
        except:
            return False, "Error from server, Status Code: {0} data returned: {1}".format(r.status_code, r.text.replace('{', '{{').replace('}', '}}'))

    def _get_error_message_from_exception(self, e):
        """ This function is used to get appropriate error message from the exception.
        :param e: Exception object
        :return: error message
        """
        error_code = None
        error_msg = "Unknown error occured"
        try:
            if hasattr(e, 'args'):
                if len(e.args) > 1:
                    error_code = e.args[0]
                    error_msg = e.args[1]
                elif len(e.args) == 1:
                    error_code = None
                    error_msg = e.args[0]
        except Exception:
            logger.debug("Error occurred while retrieving exception information")

        return "Error Code: {0}. Error Message: {1}".format(error_code, error_msg)

if __name__ == '__main__':

    logging.basicConfig(filename="rent_manager.log",
                    format='%(asctime)s %(message)s',
                    filemode='w')

    # Creating an object
    logger = logging.getLogger()
    
    # Setting the threshold of logger to DEBUG
    logger.setLevel(logging.DEBUG)

    connector = RentManagerIntegration()

    ret_val, _access_token = connector.get_token()

    if not ret_val:
        logger.debug("Error occured while fetching access token from Rent Manager. Error {}".format(_access_token))
        exit()

    # Fetch available unit types
    properties_headers = {
        'X-RM12Api-ApiToken': _access_token
    }

    unit_types_enpoint = "{}{}".format(RENTMANAGER_BASE_URL, '/UnitTypes')

    ret_val, unit_types_list = connector._make_rest_call(url=unit_types_enpoint,
                headers=properties_headers, method="get")

    if not ret_val:
        logger.debug("Error occured while fetching unit types from Rent Manager. Error {}".format(unit_types_list))

    unit_types = { unit_type['UnitTypeID']:unit_type['Name'] for unit_type in unit_types_list}

    logger.debug('unit types {}'.format(unit_types))

    properties_data = {}



    # Fetch properties
    properties_headers = {
        'X-RM12Api-ApiToken': _access_token
    }

    properties_endpoint = "{}{}".format(RENTMANAGER_BASE_URL, '/Properties?filters=IsActive,eq,true')

    ret_val, properties = connector._make_rest_call(url=properties_endpoint,
                headers=properties_headers, method="get")

    if not ret_val:
        logger.debug("Error occured while fetching properties from Rent Manager. Error {}".format(properties))
        # need to exit the code

    for property in properties:
        property_id = property.get('PropertyID')
        properties_data['PropertyName'] = property.get('Name', '')
        properties_data['ShortName'] = property.get('ShortName', '')
        properties_data['Email'] = property.get('Email', '')
        properties_data['ManagerName'] = property.get('ManagerName', '')
        properties_data['PropertyType'] = property.get('PropertyType', '')
        properties_data['TaxID'] = property.get('TaxID', '')

        if property_id:

            properties_data['PropertyID'] = property_id
            # Get properties addresses
            properties_search_details_endpoint = "{}/{}/{}/{}".format(RENTMANAGER_BASE_URL, 'Properties',property_id, 
                "Search?embeds=PrimaryAddress,DefaultBank,PhoneNumbers&fields=PrimaryAddress,DefaultBank.Name,PhoneNumbers.PhoneNumber")

            ret_val, properties_search_details = connector._make_rest_call(url=properties_search_details_endpoint,
                        headers=properties_headers, method="get")

            if not ret_val:
                logger.debug("Error occured while fetching properties addresses from Rent Manager. Error {}".format(properties_search_details))
                properties_data['Addresses'] = [{ 'Address': '', 'Street': '', 'City': '', 'State': '', 'PostalCode': '' }]
                properties_data['Bank'] = None
                properties_data['PhoneNumbers'] = []
                properties_data['OwnerDetails'] = []
            else:
                properties_data['Bank'] = properties_search_details.get('DefaultBank', {}).get('Name', '')

                properties_address = {}
                properties_phone_number_list = []
                properties_owner_list = []
                properties_images_list = []

                if properties_search_details.get('PrimaryAddress'):
                    primary_address = properties_search_details['PrimaryAddress']
                    if primary_address.get('Address'):
                        properties_address['Address'] = primary_address['Address'].replace('\r\n', ", ")
                        properties_address['Street'] = primary_address.get('Street', '')
                        properties_address['City'] = primary_address.get('City', '')
                        properties_address['State'] = primary_address.get('State', '')
                        properties_address['PostalCode'] = primary_address.get('PostalCode', '')
                    else:
                        properties_address = { 'Address': '', 'Street': '', 'City': '', 'State': '', 'PostalCode': '' }
                else:
                    properties_address = { 'Address': '', 'Street': '', 'City': '', 'State': '', 'PostalCode': '' }

                properties_data['Address'] = properties_address

                for phonenumber in properties_search_details.get('PhoneNumbers', []):
                    if phonenumber.get('PhoneNumber'):
                        properties_phone_number_list.append(phonenumber['PhoneNumber'])

                properties_data['PhoneNumbers'] = properties_phone_number_list

            # Get properties owner
            properties_owner_endpoint = "{}/{}/{}/{}".format(RENTMANAGER_BASE_URL, 'Properties',property_id,"Owners")

            ret_val, properties_owners = connector._make_rest_call(url=properties_owner_endpoint,
                        headers=properties_headers, method="get")

            if not ret_val:
                logger.debug("Error occured while fetching properties owner details from Rent Manager. Error {}".format(properties_owners))
                properties_owner_list = [ {'OwnerName': '', 'OwnerTaxID': ''} ]
            else:
                if properties_owners:
                    for owner in properties_owners:
                        properties_owner_list.append({ 'OwnerName': owner.get('DisplayName', ''), 'OwnerTaxID': owner.get('TaxID', '') })
                    
            properties_data['OwnerDetails'] = properties_owner_list


            # Get properties images
            properties_images_endpoint = "{}/{}/{}/{}".format(RENTMANAGER_BASE_URL, 'Properties',property_id,"Images?embeds=File")

            ret_val, properties_images_response = connector._make_rest_call(url=properties_images_endpoint,
                        headers=properties_headers, method="get")

            if not ret_val:
                logger.debug("Error occured while fetching properties images details from Rent Manager. Error {}".format(properties_images_response))
                properties_images_list = [ {'ImageName': '', 'DownloadURL': ''} ]
            else:
                if properties_images_response:
                    for image in properties_images_response:
                        properties_images_list.append({ 'ImageName': image.get('File', {}).get('Name', ''), 'DownloadURL': image.get('File').get('DownloadURL', '') })

            properties_data['ImageDetails'] = properties_images_list
        else:
            logger.debug("Property ID not found. Skipping a property.")

        logger.debug(properties_data)