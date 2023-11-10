import aws_cdk as core
import aws_cdk.assertions as assertions

from infra.api_stack import ApiStack

def test_sqs_queue_created():
    app = core.App()
    stack = ApiStack(app, "ApiStack")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
