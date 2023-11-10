from aws_cdk import Stack, Fn, CfnOutput
from constructs import Construct
from aws_cdk import aws_apigateway as apigateway
from aws_cdk import aws_iam as iam
from aws_cdk.aws_dynamodb import Table, ITable
from aws_cdk.aws_lambda import Function, CfnPermission, IFunction
from aws_cdk import aws_ec2 as ec2
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_cognito as cognito

import json


class ApiStack(Stack):
    __ERROR_INTEGRATION_RESPONSE_400 = apigateway.IntegrationResponse(
        selection_pattern="400",
        status_code="400",
        response_parameters={
            "method.response.header.Access-Control-Allow-Origin": "'*'"
        },
        response_templates={"application/json": '{"error": "Bad input"}'},
    )
    __ERROR_INTEGRATION_RESPONSE_500 = apigateway.IntegrationResponse(
        selection_pattern="500",
        status_code="500",
        response_parameters={
            "method.response.header.Access-Control-Allow-Origin": "'*'"
        },
        response_templates={"application/json": '{"error": "Internal Service Error"}'},
    )

    __ERROR_METHOD_RESPONSE_400 = apigateway.MethodResponse(
        status_code="400",
        response_parameters={
            "method.response.header.Access-Control-Allow-Origin": True
        },
    )

    __ERROR_METHOD_RESPONSE_500 = apigateway.MethodResponse(
        status_code="500",
        response_parameters={
            "method.response.header.Access-Control-Allow-Origin": True
        },
    )

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope=scope, id=construct_id, **kwargs)

        # nlb_arn: str = Fn.import_value(shared_value_to_import="BookApiPrivIntNlbArn")
        # nlb_dns_name: str = Fn.import_value(
        #     shared_value_to_import="BookApiPrivIntNlbDnsName"
        # )

        # nlb: elbv2.INetworkLoadBalancer = (
        #     elbv2.NetworkLoadBalancer.from_network_load_balancer_attributes(
        #         scope=self,
        #         id="BookApiPrivIntNlb",
        #         load_balancer_arn=nlb_arn,
        #         load_balancer_dns_name=nlb_dns_name,
        #     )
        # )

        # vpc_link = apigateway.VpcLink(
        #     scope=self, id="BookApiPrivIntVpcLink", targets=[nlb]
        # )

        # nlb_apigw_integration = apigateway.Integration(
        #     type=apigateway.IntegrationType.HTTP_PROXY,
        #     integration_http_method="ANY",
        #     uri=f"http://{nlb_dns_name}/{{proxy}}",
        #     options=apigateway.IntegrationOptions(
        #         connection_type=apigateway.ConnectionType.VPC_LINK,
        #         vpc_link=vpc_link,
        #         request_parameters={
        #             "integration.request.path.proxy": "method.request.path.proxy"
        #         },
        #     ),
        # )

        machine_auth_userpool_arn: str = Fn.import_value(
            shared_value_to_import="MachineAuthUserPoolArn"
        )

        machine_auth_userpool: cognito.IUserPool = cognito.UserPool.from_user_pool_arn(
            scope=self,
            id="MachineAuthUserPool",
            user_pool_arn=machine_auth_userpool_arn,
        )

        api_authorizer = apigateway.CognitoUserPoolsAuthorizer(
            scope=self,
            id="ApiAuth",
            cognito_user_pools=[machine_auth_userpool],
        )

        books_table_arn: str = Fn.import_value(shared_value_to_import="BookTableArn")

        books_table: ITable = Table.from_table_arn(
            scope=self, id="BooksTable", table_arn=books_table_arn
        )

        api_ddb_statements: list[iam.PolicyStatement] = [
            iam.PolicyStatement(
                actions=["dynamodb:*"],
                effect=iam.Effect.ALLOW,
                resources=[books_table_arn],
            )
        ]

        api_ddb_policy = iam.Policy(
            scope=self, id=f"BooksApiDdbPolicy", statements=api_ddb_statements
        )

        api_ddb_role = iam.Role(
            scope=self,
            id=f"BooksApiDdbRole",
            assumed_by=iam.ServicePrincipal(service="apigateway.amazonaws.com"),
        )

        api_ddb_role.attach_inline_policy(policy=api_ddb_policy)

        api_books_function_arn: str = Fn.import_value(
            shared_value_to_import="ApiBookFunctionArn"
        )

        api_books_function: IFunction = Function.from_function_arn(
            scope=self, id="ApiBooksFunction", function_arn=api_books_function_arn
        )

        api = apigateway.RestApi(
            scope=self,
            id="books-api",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            deploy_options=apigateway.StageOptions(
                tracing_enabled=False,
                data_trace_enabled=False,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                metrics_enabled=True,
            ),
        )

        CfnOutput(
            scope=self,
            id="BooksApiBaseUrl",
            value=str(object=api.url.rstrip("/")),
            description="Provides the URL of the API Gateway with the stage name and without trailing slash",
            export_name="BooksApiBaseUrl",
        )

        CfnPermission(
            scope=self,
            id="ApiBooksFunctionPermission",
            action="lambda:InvokeFunction",
            function_name=api_books_function_arn,
            principal="apigateway.amazonaws.com",
            source_arn=api.arn_for_execute_api(),
        )

        # api.root.add_method(http_method="ANY")

        ddb: apigateway.Resource = api.root.add_resource(path_part="ddb")
        ec2: apigateway.Resource = api.root.add_resource(path_part="ec2")
        fn: apigateway.Resource = api.root.add_resource(path_part="fn")

        # books_ec2: apigateway.Resource = ec2.add_resource(path_part="{proxy+}")
        # books_ec2.add_method(
        #     http_method="ANY",
        #     integration=nlb_apigw_integration,
        #     request_parameters={"method.request.path.proxy": True},
        # )

        books_fn: apigateway.Resource = fn.add_resource(path_part="books")

        self.__create_lambda_proxy_integration(
            lambda_function=api_books_function,
            resource=books_fn,
            http_method="GET",
            authorizer=api_authorizer,
        )

        self.__create_lambda_proxy_integration(
            lambda_function=api_books_function,
            resource=books_fn,
            http_method="POST",
            authorizer=api_authorizer,
        )

        book_fn: apigateway.Resource = books_fn.add_resource(path_part="{book_id}")

        self.__create_lambda_proxy_integration(
            lambda_function=api_books_function,
            resource=book_fn,
            http_method="GET",
            authorizer=api_authorizer,
        )

        self.__create_lambda_proxy_integration(
            lambda_function=api_books_function,
            resource=book_fn,
            http_method="PUT",
            authorizer=api_authorizer,
        )

        self.__create_lambda_proxy_integration(
            lambda_function=api_books_function,
            resource=book_fn,
            http_method="DELETE",
            authorizer=api_authorizer,
        )

        books_ddb: apigateway.Resource = ddb.add_resource(path_part="books")

        self.__create_dynamodb_integration(
            ddb_role=api_ddb_role,
            resource=books_ddb,
            authorizer=api_authorizer,
            request_templates={
                "application/json": json.dumps(
                    obj={"TableName": books_table.table_name, "Limit": 500}
                ),
            },
            response_templates={
                "application/json": """
                    #set($inputRoot = $input.path('$'))
                    { 
                        "books": [
                            #foreach($item in $inputRoot.Items) {
                                "book_id": "$item.book_id.S",
                                "book_title": "$item.book_title.S",
                                "book_desc": "$item.book_desc.S"
                            }#if($foreach.hasNext),#end
                            #end                                       
                        ],
                        "count": $inputRoot.Count
                    }
                """
            },
            http_method="GET",
            action="Scan",
        )

        self.__create_dynamodb_integration(
            ddb_role=api_ddb_role,
            resource=books_ddb,
            authorizer=api_authorizer,
            response_templates={
                "application/json": '{ "book_id": "$context.requestId" }'
            },
            request_templates={
                "application/json": """
                    {
                        "Item": {
                            "book_id": {
                                "S": "$context.requestId"
                                },
                            "book_title": { "S": "$input.path('$.book_title')" },
                            "book_desc": { "S": "$input.path('$.book_desc')" }
                        },
                        "TableName": "%s"
                    }
                """
                % (books_table.table_name)
            },
            http_method="POST",
            action="PutItem",
        )

        book_ddb: apigateway.Resource = books_ddb.add_resource(path_part="{book_id}")

        self.__create_dynamodb_integration(
            ddb_role=api_ddb_role,
            resource=book_ddb,
            authorizer=api_authorizer,
            request_templates={
                "application/json": json.dumps(
                    obj={
                        "Key": {"book_id": {"S": "$method.request.path.book_id"}},
                        "TableName": books_table.table_name,
                    }
                ),
            },
            response_templates={
                "application/json": """
                    #set($inputRoot = $input.path('$'))
                    #if($inputRoot.toString().contains("Item"))
                        #set($item = $inputRoot.Item)
                        {
                            "book_id": "$item.book_id.S",
                            "book_title": "$item.book_title.S",
                            "book_desc": "$item.book_desc.S"
                        }                       
                    #else
                        #set($context.responseOverride.status = 404)
                        { "message": "Book not found" }
                    #end                                                
                """
            },
            http_method="GET",
            action="GetItem",
        )

        self.__create_dynamodb_integration(
            ddb_role=api_ddb_role,
            resource=book_ddb,
            authorizer=api_authorizer,
            request_templates={
                "application/json": """
                    #set($inputRoot = $input.path('$'))
                    {
                        "TableName": "%s",
                        "Key": { 
                            "book_id": { 
                                "S": "$method.request.path.book_id"
                            } 
                        },
                        "UpdateExpression": "SET book_title = :title, book_desc = :desc",
                        "ExpressionAttributeValues": {
                            ":title": { "S": "$input.path('$.book_title')" },
                            ":desc": { "S": "$input.path('$.book_desc')" }        
                        }    
                    }                                                    
                """
                % (books_table.table_name)
            },
            response_templates=None,
            http_method="PUT",
            action="UpdateItem",
        )

        self.__create_dynamodb_integration(
            ddb_role=api_ddb_role,
            resource=book_ddb,
            authorizer=api_authorizer,
            request_templates={
                "application/json": json.dumps(
                    obj={
                        "Key": {"book_id": {"S": "$method.request.path.book_id"}},
                        "TableName": books_table.table_name,
                    }
                ),
            },
            response_templates=None,
            http_method="DELETE",
            action="DeleteItem",
        )

    def __create_dynamodb_integration(
        self,
        ddb_role: iam.Role,
        resource: apigateway.Resource,
        authorizer,
        response_templates: dict = None,
        request_templates: dict = None,
        action: str = "Scan",
        http_method: str = "GET",
    ) -> None:
        integration = apigateway.AwsIntegration(
            service="dynamodb",
            action=action,
            options=apigateway.IntegrationOptions(
                credentials_role=ddb_role,
                integration_responses=[
                    apigateway.IntegrationResponse(
                        status_code="200",
                        selection_pattern="200",
                        response_parameters={
                            "method.response.header.Access-Control-Allow-Origin": "'*'"
                        },
                        response_templates=response_templates,
                    ),
                    self.__ERROR_INTEGRATION_RESPONSE_400,
                    self.__ERROR_INTEGRATION_RESPONSE_500,
                ],
                request_templates=request_templates,
            ),
        )

        success_response = apigateway.MethodResponse(
            status_code="200",
            response_parameters={
                "method.response.header.Access-Control-Allow-Origin": True
            },
        )

        request_parameters: dict[str, bool] = {}

        resource.add_method(
            http_method=http_method,
            integration=integration,
            method_responses=[
                success_response,
                self.__ERROR_METHOD_RESPONSE_400,
                self.__ERROR_METHOD_RESPONSE_500,
            ],
            request_parameters=request_parameters,
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorization_scopes=["books.machines/*"],
        )

    def __create_lambda_proxy_integration(
        self,
        resource: apigateway.Resource,
        lambda_function: Function,
        http_method: str,
        authorizer,
        status_code: str = "200",
        integration_request_parameters: dict = {},
        method_request_parameters: dict = {},
    ) -> None:
        integration = apigateway.LambdaIntegration(
            handler=lambda_function,
            proxy=True,
            passthrough_behavior=apigateway.PassthroughBehavior.NEVER,
            request_parameters=integration_request_parameters,
        )

        success_response = apigateway.MethodResponse(
            status_code=status_code,
            response_parameters={
                "method.response.header.Access-Control-Allow-Origin": True,
            },
        )

        resource.add_method(
            http_method=http_method,
            integration=integration,
            method_responses=[
                success_response,
                self.__ERROR_METHOD_RESPONSE_400,
                self.__ERROR_METHOD_RESPONSE_500,
            ],
            request_models={},
            request_parameters=method_request_parameters,
            authorizer=authorizer,
            authorization_type=apigateway.AuthorizationType.COGNITO,
            authorization_scopes=["books.machines/*"],
        )
