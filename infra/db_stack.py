from aws_cdk import Stack, Tags, CfnOutput
import aws_cdk.aws_dynamodb as dynamodb

from constructs import Construct


class DbStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        api_backend_table = dynamodb.Table(
            scope=self,
            id="BookTable",
            partition_key=dynamodb.Attribute(
                name="book_id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        Tags.of(scope=api_backend_table).add(key="type", value="database")

        CfnOutput(
            scope=self,
            id="BookTableName",
            value=str(object=api_backend_table.table_name),
            description="",
            export_name="BookTableName",
        )
        CfnOutput(
            scope=self,
            id="BookTableArn",
            value=str(object=api_backend_table.table_arn),
            description="",
            export_name="BookTableArn",
        )
