import os
import pandas as pd
import openai
from openai import OpenAI, NotFoundError, AuthenticationError
from typing import Dict, Optional
from mindsdb.integrations.handlers.openai_handler import Handler as OpenAIHandler
from mindsdb.integrations.utilities.handler_utils import get_api_key
from mindsdb.utilities import log

logger = log.getLogger(__name__)


class NvidiaNimHandler(OpenAIHandler):
    """
    This handler handles connection and inference with the Nvidia Nim
    """

    name = 'nvidia_nim'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_base = 'https://integrate.api.nvidia.com/v1'
        self.api_key_name = 'nvidia_nim'
        self.default_model = 'mistralai/mixtral-8x7b-instruct-v0.1'
        self.default_mode = 'default'

    @staticmethod
    def _check_client_connection(client: OpenAI):
        """
        Check the Nvidia Nim client connection by listing models.

        Args:
            client (OpenAI): OpenAI client configured with the Nvidia Nim API credentials.

        Raises:
            Exception: If the client connection (API key) is invalid.

        Returns:
            None
        """
        try:
            client.models.list()
        except NotFoundError:
            pass
        except AuthenticationError as e:
            if e.body['code'] == 401:
                raise Exception('Invalid api key')
            raise Exception(f'Something went wrong: {e}')

    def create_engine(self, connection_args):
        """
        Validate the Nvidia NIm credentials on engine creation.

        Args:
            connection_args (dict): Connection arguments.

        Raises:
            Exception: If the handler is not configured with valid API credentials.

        Returns:
            None
        """
        connection_args = {k.lower(): v for k, v in connection_args.items()}
        api_key = connection_args.get('nvidia_nim_api_key')
        if api_key is not None:
            org = connection_args.get('api_organization')
            api_base = connection_args.get('api_base') or os.environ.get('MINDSDB_INFERENCE_BASE', "https://integrate.api.nvidia.com/v1")
            client = self._get_client(api_key=api_key, base_url=api_base, org=org)
            NvidiaNimHandler._check_client_connection(client)

    @staticmethod
    def create_validation(target, args=None, **kwargs):
        """
        Validate the Nvidia Nim credentials on model creation.

        Args:
            target (str): Target column, not required for LLMs.
            args (dict): Handler arguments.
            kwargs (dict): Handler keyword arguments.

        Raises:
            Exception: If the handler is not configured with valid API credentials.

        Returns:
            None
        """
        if 'using' not in args:
            raise Exception(
                "Nvidia Nim engine requires a USING clause! Refer to its documentation for more details."
            )
        else:
            args = args['using']

        engine_storage = kwargs['handler_storage']
        connection_args = engine_storage.get_connection_args()
        api_key = get_api_key('nvidia_nim', args, engine_storage=engine_storage)
        api_base = connection_args.get('api_base') or args.get('api_base') or os.environ.get('MINDSDB_INFERENCE_BASE', 'https://integrate.api.nvidia.com/v1')
        org = args.get('api_organization')
        client = OpenAIHandler._get_client(api_key=api_key, base_url=api_base, org=org)
        NvidiaNimHandler._check_client_connection(client)
  
    def predict(self, df: pd.DataFrame, args: Optional[Dict] = None) -> pd.DataFrame:
        """
        Call the Nvidia Nim engine to predict the next token.

        Args:
            df (pd.DataFrame): Input data.
            args (dict): Handler arguments.

        Returns:
            pd.DataFrame: Predicted data
        """
        api_key = get_api_key(self.api_key_name, args, self.engine_storage)
        supported_models = self._get_supported_models(api_key, self.api_base)
        self.chat_completion_models = [model.id for model in supported_models]
        return super().predict(df, args)

    @staticmethod
    def _get_supported_models(api_key, base_url, org=None):
        """
        Get the list of supported models for the Nvidia Nim.

        Args:
            api_key (str): API key.
            base_url (str): Base URL.
            org (str): Organization name.

        Returns:
            List: List of supported models.
        """
        client = openai.OpenAI(api_key=api_key, base_url=base_url, organization=org)
        return client.models.list()