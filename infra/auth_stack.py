from aws_cdk import Duration, Stack, CfnOutput, Tags
from constructs import Construct
import aws_cdk.aws_cognito as cognito

from aws_cdk.aws_secretsmanager import Secret
import random
import string


class AuthStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope=scope, id=construct_id, **kwargs)

        random_string: str = "".join(
            random.choices(population=string.ascii_uppercase + string.digits, k=6)
        )

        cognito_machine_auth_domain_prefix: str = (
            f"books-api-machine-auth-{random_string}".lower()
        )

        full_access_scope = cognito.ResourceServerScope(
            scope_name="*", scope_description="Full access"
        )

        machine_user_pool = cognito.UserPool(
            scope=self, id="MachineAuthUserPool", self_sign_up_enabled=False
        )

        machine_user_pool_resource_server: cognito.UserPoolResourceServer = (
            machine_user_pool.add_resource_server(
                id="MachineAuthResourceServer",
                identifier="books.machines",
                scopes=[full_access_scope],
            )
        )

        machine_user_pool_client: cognito.UserPoolClient = machine_user_pool.add_client(
            id="MachineAuthUserPoolClient",
            id_token_validity=Duration.days(amount=1),
            access_token_validity=Duration.days(amount=1),
            generate_secret=True,
            prevent_user_existence_errors=True,
            auth_flows=cognito.AuthFlow(
                custom=True,
                user_password=False,
                user_srp=False,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=False,
                    implicit_code_grant=False,
                    client_credentials=True,
                ),
                scopes=[
                    cognito.OAuthScope.resource_server(
                        server=machine_user_pool_resource_server,
                        scope=full_access_scope,
                    )
                ],
            ),
        )

        machine_user_pool_domain: cognito.UserPoolDomain = machine_user_pool.add_domain(
            id="MachineAuthUserPoolDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=cognito_machine_auth_domain_prefix
            ),
        )

        machine_user_pool_client_secret: Secret = Secret(
            scope=self,
            id="MachineAuthUserPoolClientIdSecret",
            description="Client Secret for the Machine User Pool Client.",
            secret_string_value=machine_user_pool_client.user_pool_client_secret,
        )

        cognito_access_token_url: str = f"https://{machine_user_pool_domain.domain_name}.auth.{self.region}.amazoncognito.com/oauth2/token"

        Tags.of(scope=self).add(key="type", value="auth")

        CfnOutput(
            scope=self,
            id="MachineAuthUserPoolArn",
            value=str(object=machine_user_pool.user_pool_arn),
            description="",
            export_name="MachineAuthUserPoolArn",
        )

        CfnOutput(
            self,
            "MachineAuthUserPoolClientSecretArn",
            value=str(machine_user_pool_client_secret.secret_full_arn),
            description="",
            export_name="MachineAuthUserPoolClientSecretArn",
        )

        CfnOutput(
            self,
            "MachineAuthUserPoolClientSecretName",
            value=str(machine_user_pool_client_secret.secret_name),
            description="",
            export_name="MachineAuthUserPoolClientSecretName",
        )

        CfnOutput(
            self,
            "MachineAuthUserPoolClientId",
            value=str(machine_user_pool_client.user_pool_client_id),
            description="",
            export_name="MachineAuthUserPoolClientId",
        )

        CfnOutput(
            scope=self,
            id="MachineAuthCognitoDomainName",
            value=str(object=machine_user_pool_domain.domain_name),
            description="",
            export_name="MachineAuthCognitoDomainName",
        )

        CfnOutput(
            scope=self,
            id="MachineAuthCognitoAccessTokenUrl",
            value=str(object=cognito_access_token_url),
            description="Provides the URL for Oauth2 of the User Pool in the format 'https://{user_pool_domain_name}.auth.{aws_region}.amazoncognito.com/oauth2/token'",
            export_name="MachineAuthCognitoAccessTokenUrl",
        )
