#!/usr/bin/env python3
import os

import aws_cdk as cdk

from infra.api_stack import ApiStack
from infra.db_stack import DbStack
from infra.lambda_stack import LambdaStack
from infra.ec2_stack import Ec2Stack
from infra.test_pipeline_stack import TestPipelineStack
from infra.auth_stack import AuthStack


app = cdk.App()

CDK_ENV = cdk.Environment(
    account=os.environ["CDK_DEFAULT_ACCOUNT"],
    region=os.environ.get("CDK_DEPLOY_REGION", default="eu-central-1"),
)

auth_stack = AuthStack(scope=app, construct_id="AuthStack", env=CDK_ENV)
api_stack = ApiStack(scope=app, construct_id="ApiStack", env=CDK_ENV)
lambda_stack = LambdaStack(scope=app, construct_id="LambdaStack", env=CDK_ENV)
db_stack = DbStack(scope=app, construct_id="DbStack", env=CDK_ENV)
ec2_stack = Ec2Stack(scope=app, construct_id="Ec2Stack", env=CDK_ENV)

test_pipeline_stack = TestPipelineStack(
    scope=app, construct_id="TestPipelineStack", env=CDK_ENV
)


lambda_stack.add_dependency(target=db_stack)

api_stack.add_dependency(target=auth_stack)
api_stack.add_dependency(target=db_stack)
api_stack.add_dependency(target=lambda_stack)
api_stack.add_dependency(target=ec2_stack)

test_pipeline_stack.add_dependency(target=api_stack)
test_pipeline_stack.add_dependency(target=auth_stack)


cdk.Tags.of(scope=app).add(key="app", value="BooksApi")


app.synth()
