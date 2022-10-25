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
    units_headers = {
        'X-RM12Api-ApiToken': _access_token
    }

    units_endpoint = "{}{}".format(RENTMANAGER_BASE_URL, '/Units/OnlineListings')

    ret_val, units = connector._make_rest_call(url=units_endpoint,
                headers=units_headers, method="get")

    if not ret_val:
        logger.debug("Error occured while fetching units from Rent Manager. Error {}".format(units))

    for unit in units:

        units_data = {}

        unit_id = unit.get('UnitID')

        if unit_id:
            
            units_data['UnitID'] = unit_id
            units_data['UnitName'] = unit.get('UnitName', '')
            units_data['Bedrooms'] = unit.get('Bedrooms', '')
            units_data['Bathrooms'] = unit.get('Bathrooms', '')
            units_data['PropertyID'] = unit.get('PropertyID', '')
            units_data['PropertyType'] = unit.get('PropertyType', '')

            # Get unit addresses
            unit_search_endpoint = "{}/{}/{}/{}".format(RENTMANAGER_BASE_URL, 'Units', unit_id,
            "Search?embeds=PrimaryAddress,Amenities,MarketRent,Floor,UnitType&" \
                "fields=PrimaryAddress,Amenities.Name,MarketRent.Amount,SquareFootage,MaxOccupancy,Floor.Name,UnitType.UnitTypeID")

            ret_val, unit_search_data = connector._make_rest_call(url=unit_search_endpoint,
                        headers=units_headers, method="get")

            if not ret_val:
                logger.debug("Error occured while fetching units details from Rent Manager. Error {}".format(unit_search_data))
                units_data['Addresses'] = [{ 'Address': '', 'Street': '', 'City': '', 'State': '', 'PostalCode': '' }]
                units_data['Amenities'] = []
                units_data['MarketRent'] = []
                units_data['clear'] = ''
                units_data['MaxOccupancy'] = ''
                units_data['Floor'] = ''
                units_data['UnitType'] = ''
            else:
                units_data['SquareFootage'] = unit_search_data.get('SquareFootage', '')
                units_data['MaxOccupancy'] = unit_search_data.get('MaxOccupancy', '')
                units_data['UnitType'] = unit_search_data.get('UnitType', {}).get('UnitTypeID', '')
                units_data['Floor'] = unit_search_data.get('Floor', {}).get('Name', '')

                unit_address = {}
                units_amenities_list = []
                units_market_rent_list = []

                if unit_search_data.get('PrimaryAddress'):
                    primary_address = unit_search_data['PrimaryAddress']
                    if primary_address.get('Address'):
                        unit_address['Address'] = primary_address['Address'].replace('\r\n', ", ")
                        unit_address['Street'] = primary_address.get('Street', '')
                        unit_address['City'] = primary_address.get('City', '')
                        unit_address['State'] = primary_address.get('State', '')
                        unit_address['PostalCode'] = primary_address.get('PostalCode', '')
                    else:
                        unit_address = { 'Address': '', 'Street': '', 'City': '', 'State': '', 'PostalCode': '' }
                else:
                    unit_address = { 'Address': '', 'Street': '', 'City': '', 'State': '', 'PostalCode': '' }

                units_data['Address'] = unit_address

                for amenity in unit_search_data.get('Amenities', []):
                    if amenity.get('Name'):
                        units_amenities_list.append(amenity['Name'])

                units_data['Amenities'] = units_amenities_list

                for rent in unit_search_data.get('MarketRent', []):
                    if rent.get('Amount'):
                        units_market_rent_list.append(rent['Amount'])
                
                units_data['MarketRent'] = units_market_rent_list
        else:
            logger.debug("Unit ID not found. Skipping a unit.")

        logger.debug(units_data)
