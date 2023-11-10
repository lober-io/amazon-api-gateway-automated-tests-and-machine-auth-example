from aws_cdk import Duration, Stack, Fn, CfnOutput, Tags
from constructs import Construct
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_elasticloadbalancingv2 as elbv2
import aws_cdk.aws_elasticloadbalancingv2_targets as elbv2_targets
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_assets as s3_assets
from aws_cdk import aws_iam as iam


class Ec2Stack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope=scope, id=construct_id, **kwargs)

        book_table_name: str = Fn.import_value(shared_value_to_import="BookTableName")
        books_table_arn: str = Fn.import_value(shared_value_to_import="BookTableArn")

        vpc: ec2.IVpc = ec2.Vpc.from_lookup(scope=self, id="Vpc", is_default=True)

        # Create an network load-balancer
        nlb = elbv2.NetworkLoadBalancer(
            scope=self,
            id="BookApiPrivIntNlb",
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC, one_per_az=True
            ),
            internet_facing=False,
        )

        nlb_http_listener: elbv2.NetworkListener = nlb.add_listener(
            id="BookApiPrivIntNlbHttpListner", port=80
        )

        software_s3_asset_index = s3_assets.Asset(
            scope=self,
            id="BookApiEc2SoftwareAssetIndex",
            path="assets/ec2/api_book/index.js",
        )

        software_s3_asset_package = s3_assets.Asset(
            scope=self,
            id="BookApiEc2SoftwareAssetPackage",
            path="assets/ec2/api_book/package.json",
        )

        software_s3_asset_install = s3_assets.Asset(
            scope=self,
            id="BookApiEc2SoftwareAssetInstall",
            path="assets/ec2/api_book/install.sh",
        )

        ec2_init_data: ec2.CloudFormationInit = ec2.CloudFormationInit.from_elements(
            ec2.InitFile.from_existing_asset(
                target_file_name="/opt/book_api/index.js", asset=software_s3_asset_index
            ),
            ec2.InitFile.from_existing_asset(
                target_file_name="/opt/book_api/package.json",
                asset=software_s3_asset_package,
            ),
            ec2.InitFile.from_existing_asset(
                target_file_name="/opt/book_api_install.sh",
                asset=software_s3_asset_install,
                mode="000755",
            ),
            ec2.InitCommand.shell_command(
                shell_command="sudo yum install -y gcc-c++ make"
            ),
            ec2.InitCommand.shell_command(
                shell_command="sudo /opt/book_api_install.sh"
            ),
            ec2.InitService.systemd_config_file(
                service_name="book_api",
                command="/opt/.nvm/versions/node/v16.0.0/bin/node /opt/book_api/index.js",
                cwd="/opt/book_api/",
            ),
            ec2.InitService.enable(
                service_name="book_api", service_manager=ec2.ServiceManager.SYSTEMD
            ),
        )

        ec2_sg = ec2.SecurityGroup(
            scope=self,
            id="Ec2SgHttpIn",
            vpc=vpc,
            description="",
            allow_all_outbound=True,
        )

        ec2_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(cidr_ip=vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(port=80),
            description="Allow HTTP from Load Balancer",
        )

        ec2_instance = ec2.Instance(
            scope=self,
            id="Ec2Instance",
            instance_type=ec2.InstanceType(instance_type_identifier="t3.small"),
            machine_image=ec2.AmazonLinuxImage(
                generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC, one_per_az=True
            ),
            security_group=ec2_sg,
            block_devices=[
                ec2.BlockDevice(
                    device_name="/dev/xvda",
                    volume=ec2.BlockDeviceVolume.ebs(volume_size=10),
                )
            ],
            detailed_monitoring=True,
            associate_public_ip_address=True,
            init=ec2_init_data,
            init_options=ec2.ApplyCloudFormationInitOptions(
                timeout=Duration.minutes(amount=15),
                print_log=True,
                ignore_failures=True,
            ),
        )

        ec2_instance.role.add_managed_policy(
            policy=iam.ManagedPolicy.from_aws_managed_policy_name(
                managed_policy_name="AmazonSSMManagedInstanceCore"
            )
        )

        software_s3_asset_index.grant_read(grantee=ec2_instance.role)
        software_s3_asset_package.grant_read(grantee=ec2_instance.role)
        software_s3_asset_install.grant_read(grantee=ec2_instance.role)

        ec2_ddb_iam_policy = iam.Policy(
            scope=self,
            id="BookApiEc2DynamodDBPolicy",
            policy_name="BookApiEc2DynamodDBPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "dynamodb:Scan",
                        "dynamodb:Query",
                        "dynamodb:PutItem",
                        "dynamodb:UpdateItem",
                        "dynamodb:DeleteItem",
                    ],
                    resources=[books_table_arn],
                )
            ],
        )

        ec2_instance.role.add_managed_policy(policy=ec2_ddb_iam_policy)

        ec2_instance.add_to_role_policy(
            statement=iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "dynamodb:Scan",
                    "dynamodb:Query",
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                ],
                resources=[books_table_arn],
            )
        )
        # Add targets on a particular port.
        nlb_http_target_group: elbv2.NetworkTargetGroup = nlb_http_listener.add_targets(
            id="Ec2Instances",
            port=80,
            targets=[elbv2_targets.InstanceTarget(instance=ec2_instance)],
            # targets=[],
        )

        nlb_http_target_group.configure_health_check(
            interval=Duration.seconds(amount=5),
            timeout=Duration.seconds(amount=2),
            healthy_threshold_count=2,
            unhealthy_threshold_count=2,
        )

        CfnOutput(
            scope=self,
            id="BookApiPrivIntNlbArn",
            value=str(object=nlb.load_balancer_arn),
            description="",
            export_name="BookApiPrivIntNlbArn",
        )

        CfnOutput(
            scope=self,
            id="BookApiPrivIntNlbDnsName",
            value=str(object=nlb.load_balancer_dns_name),
            description="",
            export_name="BookApiPrivIntNlbDnsName",
        )
