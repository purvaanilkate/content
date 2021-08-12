from CommonServerPython import *
import traceback
import urllib3

# Disable insecure warnings
urllib3.disable_warnings()

ERROR_CODES_TO_SKIP = [
    404
]

''' GLOBAL VARIABLES '''
URI_PREFIX = '/services/data/v51.0/'

'''CLIENT CLASS'''


class Client(BaseClient):
    """ A client class that implements logic to authenticate with the application. """

    def test(self):
        """ Tests connectivity with the application. """

        uri = URI_PREFIX + 'sobjects/User/testid'
        self._http_request(method='GET', url_suffix=uri)

    def get_user_by_id(self, user_id: str) -> Optional['IAMUserAppData']:
        """ Queries the user in the application using REST API by its ID, and returns an IAMUserAppData object
        that holds the user_id, username, is_active and app_data attributes given in the query response.

        :type user_id: ``str``
        :param user_id: ID of the user in the application.

        :return: An IAMUserAppData object if user exists, None otherwise.
        :rtype: ``Optional[IAMUserAppData]``
        """
        uri = f'{URI_PREFIX}sobjects/FF__Key_Contact__c/{user_id}'

        res = self._http_request(
            method='GET',
            url_suffix=uri
        )

        if res:
            username = res.get('Work_Email__c')
            is_active = True

            return IAMUserAppData(user_id, username, is_active, res)
        return None

    def get_user(self, email: str) -> Optional['IAMUserAppData']:
        """ Queries the user in the application using REST API by its email, and returns an IAMUserAppData object
        that holds the user_id, username, is_active and app_data attributes given in the query response.

        :type email: ``str``
        :param email: Email address of the user

        :return: An IAMUserAppData object if user exists, None otherwise.
        :rtype: ``Optional[IAMUserAppData]``
        """
        uri = f'{URI_PREFIX}parameterizedSearch/'
        params = {
            "q": email,
            "sobject": "FF__Key_Contact__c",
            "FF__Key_Contact__c.where": f"Work_Email__c='{email}'",
            "FF__Key_Contact__c.fields": "Id, FF__First_Name__c, FF__Last_Name__c,Work_Email__c,Name"
        }

        res = self._http_request(
            method='GET',
            url_suffix=uri,
            params=params
        )

        user_app_data = res.get('searchRecords', [])

        if user_app_data:
            user_id = user_app_data[0].get('Id')
            return self.get_user_by_id(user_id)
        return None

    def create_user(self, user_data: Dict[str, Any]) -> 'IAMUserAppData':
        """ Creates a user in the application using REST API.

        :type user_data: ``Dict[str, Any]``
        :param user_data: User data in the application format

        :return: An IAMUserAppData object that contains the data of the created user in the application.
        :rtype: ``IAMUserAppData``
        """
        uri = f'{URI_PREFIX}sobjects/FF__Key_Contact__c'

        res = self._http_request(
            method='POST',
            url_suffix=uri,
            json_data=user_data
        )

        user_id = res.get('id')
        username = res.get('userName')
        is_active = True

        return IAMUserAppData(user_id, username, is_active, res)

    def update_user(self, user_id: str, user_data: Dict[str, Any]):
        """ Updates a user in the application using REST API.

        :type user_id: ``str``
        :param user_id: ID of the user in the application

        :type user_data: ``Dict[str, Any]``
        :param user_data: User data in the application format

        :return: An IAMUserAppData object that contains the data of the updated user in the application.
        :rtype: ``IAMUserAppData``
        """
        uri = f'{URI_PREFIX}sobjects/FF__Key_Contact__c/{user_id}'
        params = {"_HttpMethod": "PATCH"}
        self._http_request(
            method='POST',
            url_suffix=uri,
            params=params,
            json_data=user_data
        )

        return self.get_user_by_id(user_id)

    def enable_user(self, user_id: str):
        """ Enables a user in the application using REST API.
        There is no action on the user for Salesforce Fusion instance needs to be taken.

        :type user_id: ``str``
        :param user_id: ID of the user in the application

        :return: An IAMUserAppData object that contains the data of the user in the application.
        :rtype: ``IAMUserAppData``
        """

        return self.get_user_by_id(user_id)

    def disable_user(self, user_id: str) -> 'IAMUserAppData':
        """ Removes a user in the application using REST API.

        :type user_id: ``str``
        :param user_id: ID of the user in the application

        :return: An IAMUserAppData object that contains the data of the user in the application.
        :rtype: ``IAMUserAppData``
        """

        uri = f'{URI_PREFIX}sobjects/FF__Key_Contact__c/{user_id}'

        self._http_request(
            method='DELETE',
            url_suffix=uri
        )

        return IAMUserAppData(user_id, "", False, {})

    def get_app_fields(self) -> Dict[str, Any]:
        """ Gets a dictionary of the user schema fields in the application and their description.

        :return: The user schema fields dictionary
        :rtype: ``Dict[str, str]``
        """

        uri = f'{URI_PREFIX}sobjects/FF__Key_Contact__c/describe/'
        res = self._http_request(
            method='GET',
            url_suffix=uri
        )

        fields = res.get('result', [])
        return {field.get('name'): field.get('label') for field in fields}

    @staticmethod
    def handle_exception(user_profile, e, action):
        """ Handles failed responses from the application API by setting the User Profile object with the result.
            The result entity should contain the following data:
            1. action        (``IAMActions``)       The failed action                       Required
            2. success       (``bool``)             The success status                      Optional (by default, True)
            3. skip          (``bool``)             Whether or not the command was skipped  Optional (by default, False)
            3. skip_reason   (``str``)              Skip reason                             Optional (by default, None)
            4. error_code    (``Union[str, int]``)  HTTP error code                         Optional (by default, None)
            5. error_message (``str``)              The error description                   Optional (by default, None)

            Note: This is the place to determine how to handle specific edge cases from the API, e.g.,
            when a DISABLE action was made on a user which is already disabled and therefore we can't
            perform another DISABLE action.

        :type user_profile: ``IAMUserProfile``
        :param user_profile: The user profile object

        :type e: ``Union[DemistoException, Exception]``
        :param e: The exception object - if type is DemistoException, holds the response json object (`res` attribute)

        :type action: ``IAMActions``
        :param action: An enum represents the current action (GET, UPDATE, CREATE, DISABLE or ENABLE)
        """
        if isinstance(e, DemistoException) and e.res is not None:
            error_code = e.res.status_code

            if action == IAMActions.DISABLE_USER and error_code in ERROR_CODES_TO_SKIP:
                skip_message = 'Users is already disabled or does not exist in the system.'
                user_profile.set_result(action=action,
                                        skip=True,
                                        skip_reason=skip_message)

            try:
                resp = e.res.json()
                error_message = get_error_details(resp)
            except ValueError:
                error_message = str(e)
        else:
            error_code = ''
            error_message = str(e)

        user_profile.set_result(action=action,
                                success=False,
                                error_code=error_code,
                                error_message=error_message)

        demisto.error(traceback.format_exc())


'''HELPER FUNCTIONS'''


def get_error_details(res: Dict[str, Any]) -> str:
    """ Parses the error details retrieved from the application and outputs the resulted string.

    :type res: ``Dict[str, Any]``
    :param res: The error data retrieved from the application.

    :return: The parsed error details.
    :rtype: ``str``
    """
    message = res.get('message')
    details = res.get('detail')
    return f'{message}: {details}'


'''COMMAND FUNCTIONS'''


def test_module(client: Client):
    """ Tests connectivity with the client. """

    client.test()
    return_results('ok')


def get_mapping_fields(client: Client) -> GetMappingFieldsResponse:
    """ Creates and returns a GetMappingFieldsResponse object of the user schema in the application

    :param client: (Client) The integration Client object that implements a get_app_fields() method
    :return: (GetMappingFieldsResponse) An object that represents the user schema
    """
    app_fields = client.get_app_fields()
    incident_type_scheme = SchemeTypeMapping(type_name=IAMUserProfile.DEFAULT_INCIDENT_TYPE)

    for field, description in app_fields.items():
        incident_type_scheme.add_field(field, description)

    return GetMappingFieldsResponse([incident_type_scheme])


def main():
    user_profile = None
    params = demisto.params()
    base_url = urljoin(params['url'].strip('/'), '/api/now/')
    username = params.get('credentials', {}).get('identifier')
    password = params.get('credentials', {}).get('password')
    mapper_in = params.get('mapper_in')
    mapper_out = params.get('mapper_out')
    verify_certificate = not params.get('insecure', False)
    proxy = params.get('proxy', False)
    command = demisto.command()
    args = demisto.args()

    is_create_enabled = params.get("create_user_enabled")
    is_enable_enabled = params.get("enable_user_enabled")
    is_disable_enabled = params.get("disable_user_enabled")
    is_update_enabled = params.get("update_user_enabled")
    create_if_not_exists = params.get("create_if_not_exists")

    iam_command = IAMCommand(is_create_enabled, is_enable_enabled, is_disable_enabled, is_update_enabled,
                             create_if_not_exists, mapper_in, mapper_out)

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }

    client = Client(
        base_url=base_url,
        verify=verify_certificate,
        proxy=proxy,
        headers=headers,
        ok_codes=(200, 201),
        auth=(username, password)
    )

    demisto.debug(f'Command being called is {command}')

    '''CRUD commands'''

    if command == 'iam-get-user':
        user_profile = iam_command.get_user(client, args)

    elif command == 'iam-create-user':
        user_profile = iam_command.create_user(client, args)

    elif command == 'iam-update-user':
        user_profile = iam_command.update_user(client, args)

    elif command == 'iam-disable-user':
        user_profile = iam_command.disable_user(client, args)

    if user_profile:
        return_results(user_profile)

    '''non-CRUD commands'''

    try:
        if command == 'test-module':
            test_module(client)

        elif command == 'get-mapping-fields':
            return_results(get_mapping_fields(client))

    except Exception as exc:
        # For any other integration command exception, return an error
        return_error(f'Failed to execute the {command} command.\nError: {exc}',
                     error=f'Traceback: {traceback.format_exc()}')


from IAMApiModule import * # noqa E402

if __name__ in ('__main__', '__builtin__', 'builtins'):
    main()
