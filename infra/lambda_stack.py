from aws_cdk import Duration, Stack, Fn, CfnOutput, Tags
from constructs import Construct
from aws_cdk import aws_lambda_python_alpha

from aws_cdk import aws_iam as iam
from aws_cdk.aws_lambda import (
    Runtime,
    Tracing,
    Architecture,
    LambdaInsightsVersion,
)


class LambdaStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope=scope, id=construct_id, **kwargs)

        book_table_name: str = Fn.import_value(shared_value_to_import="BookTableName")
        books_table_arn: str = Fn.import_value(shared_value_to_import="BookTableArn")

        api_book_function = aws_lambda_python_alpha.PythonFunction(
            scope=self,
            id="ApiBookFunction",
            function_name="ApiBookFunction",
            runtime=Runtime.PYTHON_3_10,
            entry="assets/functions/api_book",
            index="api_book.py",
            handler="lambda_handler",
            environment={
                "BOOKS_TABLE_NAME": book_table_name,
                "POWERTOOLS_SERVICE_NAME": "books_api",
                "REGION": self.region,
            },
            architecture=Architecture.ARM_64,
            timeout=Duration.minutes(amount=10),
            memory_size=2048,
            tracing=Tracing.DISABLED,
            insights_version=LambdaInsightsVersion.VERSION_1_0_229_0,
        )

        api_book_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:GetItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:PutItem",
                    "dynamodb:DeleteItem",
                    "dynamodb:Scan",
                    "dynamodb:Query",
                ],
                resources=[books_table_arn],
            )
        )

        api_book_function.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=["*"],
            )
        )

        Tags.of(scope=api_book_function).add(key="type", value="function")

        CfnOutput(
            scope=self,
            id="ApiBookFunctionArn",
            value=str(object=api_book_function.function_arn),
            description="Contains the ARN of the Books API backend function.",
            export_name="ApiBookFunctionArn",
        )
