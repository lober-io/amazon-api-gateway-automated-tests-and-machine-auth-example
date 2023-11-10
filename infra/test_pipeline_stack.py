from aws_cdk import Stack, Fn, Tags, SecretValue
from aws_cdk import SecretValue
from constructs import Construct

from aws_cdk.aws_codepipeline import Pipeline, Artifact
from aws_cdk.aws_codebuild import (
    PipelineProject,
    BuildEnvironmentVariable,
    BuildEnvironment,
    LinuxBuildImage,
    ComputeType,
    BuildSpec,
)
from aws_cdk.aws_iam import PolicyStatement

from aws_cdk.aws_codepipeline_actions import (
    CodeBuildAction,
    GitHubSourceAction,
)


class TestPipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope=scope, id=construct_id, **kwargs)

        machine_user_pool_client_secret_arn = Fn.import_value(
            shared_value_to_import="MachineAuthUserPoolClientSecretArn"
        )

        machine_user_pool_client_id = Fn.import_value(
            shared_value_to_import="MachineAuthUserPoolClientId"
        )

        api_base_url: str = Fn.import_value(shared_value_to_import="BooksApiBaseUrl")

        cognito_machine_auth_domain_name: str = Fn.import_value(
            shared_value_to_import="MachineAuthCognitoDomainName"
        )

        api_access_token_url: str = Fn.import_value(
            shared_value_to_import="MachineAuthCognitoAccessTokenUrl"
        )

        github_owner = self.node.try_get_context("github_owner")
        github_repository_name = self.node.try_get_context("github_repository_name")

        github_repository_branch = self.node.try_get_context("github_branch")

        github_token_secret_store_name = self.node.try_get_context(
            key="github_token_secret_store_name"
        )
        github_access_token_secret: SecretValue = SecretValue.secrets_manager(
            secret_id=github_token_secret_store_name
        )

        pipeline = Pipeline(scope=self, id="BooksApiTestPipeline")

        source_output = Artifact()

        source_action = GitHubSourceAction(
            action_name="Github_Source",
            output=source_output,
            owner=github_owner,
            repo=github_repository_name,
            branch=github_repository_branch,
            oauth_token=github_access_token_secret,
        )

        source_stage = pipeline.add_stage(stage_name="Source", actions=[source_action])

        api_test_project = PipelineProject(
            scope=self,
            id="BooksApiTestPipelineProject",
            build_spec=BuildSpec.from_source_filename(
                filename="tests/api/buildspec.yml"
            ),
            environment=BuildEnvironment(
                build_image=LinuxBuildImage.STANDARD_7_0,
                compute_type=ComputeType.SMALL,
            ),
            environment_variables={},
        )

        api_test_project.add_to_role_policy(
            statement=PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:DescribeSecret",
                ],
                resources=[machine_user_pool_client_secret_arn],
            )
        )

        api_test_action = CodeBuildAction(
            action_name="ApiTests",
            project=api_test_project,
            input=source_output,
            environment_variables={
                "API_BASE_URl": BuildEnvironmentVariable(value=api_base_url),
                "API_ACCESS_TOKEN_URL": BuildEnvironmentVariable(
                    value=api_access_token_url
                ),
                "API_CLIENT_ID": BuildEnvironmentVariable(
                    value=machine_user_pool_client_id
                ),
                "API_CLIENT_SECRET": BuildEnvironmentVariable(
                    value=machine_user_pool_client_secret_arn
                ),
            },
        )

        api_test_stage = pipeline.add_stage(
            stage_name="ApiTests", actions=[api_test_action]
        )

        Tags.of(scope=self).add(key="type", value="pipeline")
        Tags.of(scope=self).add(key="subtype", value="cdk")
