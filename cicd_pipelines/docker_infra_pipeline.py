from aws_cdk import (
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_codedeploy as codedeploy,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as pipelineactions,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elb,
    aws_iam as iam,
    aws_s3 as s3,
    CfnOutput,
    Stack,
    SecretValue,
)
from constructs import Construct
import os


class DockerInfraPipeline(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, env=kwargs["env"])

        # Extracting parameters from kwargs
        target_account = kwargs["target_account"]
        target_region = kwargs["target_region"]
        env_name = kwargs["env_name"]
        repo_name = kwargs["repo_name"]
        branch = kwargs["branch"]
        artifacts_bucket = kwargs["artifacts_bucket"]

        # ==================================================
        # ==================== VPC =========================
        # ==================================================

        # Define subnet configurations
        public_subnet = ec2.SubnetConfiguration(
            name="Public", subnet_type=ec2.SubnetType.PUBLIC, cidr_mask=28
        )
        private_subnet = ec2.SubnetConfiguration(
            name="Private", subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, cidr_mask=28
        )

        # Create VPC
        cluster_vpc = ec2.Vpc(
            scope=self,
            id="VPC",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/24"),
            max_azs=2,
            nat_gateway_provider=ec2.NatProvider.gateway(),
            nat_gateways=1,
            subnet_configuration=[public_subnet, private_subnet],
        )
        cluster_vpc.add_gateway_endpoint(
            "S3Endpoint", service=ec2.GatewayVpcEndpointAwsService.S3
        )

        # Access existing S3 bucket
        existing_bucket = s3.Bucket.from_bucket_name(
            self, "ExistingBucket", artifacts_bucket
        )

        # ==================================================
        # ================= IAM Role =======================
        # ==================================================

        # Create IAM role for the pipeline
        pipeline_role = iam.Role(
            self,
            "pipeline_role",
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("codepipeline.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
                iam.ServicePrincipal("cloudformation.amazonaws.com"),
            ),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AWSCodeBuildAdminAccess"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonEC2ContainerRegistryPowerUser"
                ),
            ],
            role_name=construct_id + "-role",
        )

        # Add permissions to the pipeline role
        pipeline_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess")
        )
        pipeline_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess")
        )

        pipeline_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["sts:AssumeRole", "codestar-connections:UseConnection"],
                resources=["*"],
            )
        )

        # ==================================================
        # ================= ECR Repository =================
        # ==================================================

        # Create Elastic Container Registry (ECR) image repository
        image_repo = ecr.Repository(self, "ImageRepo")

        # ==================================================
        # =============== ECS Task Definition ===============
        # ==================================================

        # Create Task Definition for the ECS Fargate service
        fargate_task_def = ecs.FargateTaskDefinition(self, "FargateTaskDef")
        fargate_task_def.add_container(
            "Container",
            container_name="myweb",
            image=ecs.ContainerImage.from_ecr_repository(image_repo),
            port_mappings=[{"containerPort": 80}],
            memory_limit_mib=512,
            cpu=256,
        )
        # Creates a new blue Target Group that routes traffic from the public Application Load Balancer (ALB) to the
        # registered targets within the Target Group e.g. (EC2 instances, IP addresses, Lambda functions)
        # https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
        target_group_blue = elb.ApplicationTargetGroup(
            self, "BlueTargetGroup",
            target_group_name= construct_id[:18].strip() + "alb-blue-tg",
            target_type=elb.TargetType.IP,
            port=80,
            vpc=cluster_vpc
        )

        # Creates a new green Target Group
        target_group_green = elb.ApplicationTargetGroup(
            self, "GreenTargetGroup",
            target_group_name= construct_id[:18].strip() + "alb-green-tg",
            target_type=elb.TargetType.IP,
            port=80,
            vpc=cluster_vpc
        )

        # ==================================================
        # ========== Application Load Balancer ==============
        # ==================================================

        # Create Security Group for the Application Load Balancer (ALB)

        # Create a new Security Group for the Application Load Balancer (ALB)
        albSg = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",  # The ID for the security group
            vpc=cluster_vpc,  # The VPC in which the security group is created
            allow_all_outbound=True,  # Allow all outbound traffic from the security group
        )

        # Add an ingress rule to the security group to allow inbound traffic on port 80 (HTTP)
        albSg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),  # Allow traffic from any IPv4 address
            connection=ec2.Port.tcp(80),  # Allow TCP traffic on port 80
            description="Allows access on port 80/http",  # Description for the ingress rule
            remote_rule=False,  # Whether the rule is a remote rule (not applied to this security group itself)
        )

        # Create a public Application Load Balancer (ALB)
        public_alb = elb.ApplicationLoadBalancer(
            self,
            "PublicAlb",  # The ID for the ALB
            vpc=cluster_vpc,  # The VPC in which the ALB is created
            internet_facing=True,  # Specify if the ALB should be internet-facing
            security_group=albSg,  # Assign the previously created security group to the ALB
        )

        # Add a listener to the ALB on port 80
        alb_listener = public_alb.add_listener(
            "AlbListener80",  # The ID for the listener
            open=False,  # Specify if the listener is open (true) or closed (false)
            port=80,  # The port on which the listener listens
            default_target_groups=[
                target_group_blue
            ],  # Default target groups for the listener
        )

        # ==================================================
        # ============= ECS Fargate Service =================
        # ==================================================

        # Create ECS Fargate service
        # Create an ECS Fargate service
        fargate_service = ecs.FargateService(
            self,
            "FargateService",  # The ID for the Fargate service
            desired_count=1,  # The desired number of tasks for the service
            service_name="fargate-frontend-service",  # The name of the ECS service
            task_definition=fargate_task_def,  # The task definition for the service
            cluster=ecs.Cluster(
                self,
                "EcsCluster",  # The ID for the ECS cluster
                enable_fargate_capacity_providers=True,  # Enable Fargate capacity providers for the cluster
                vpc=cluster_vpc,  # The VPC in which the cluster is created
            ),
            # Specify the deployment controller for the service
            deployment_controller=ecs.DeploymentController(
                type=ecs.DeploymentControllerType.CODE_DEPLOY
            ),
            assign_public_ip=True,  # Assign public IP addresses to the tasks in the service
            # Select the VPC subnets for the service
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC  # Select public subnets for the service
            ),
            security_groups=[albSg],  # Assign the security group to the service
        )

        # Add the ECS Fargate service to the ALB target group
        fargate_service.attach_to_application_target_group(target_group_blue)

        # ==================================================
        # ============= CodeCommit Repository ===============
        # ==================================================

        # Access CodeCommit repository
        repository = codecommit.Repository.from_repository_name(
            self, "MyCodeCommitRepo", repository_name=repo_name
        )

        # ==================================================
        # =============== CodeBuild Project =================
        # ==================================================

        # Create CodeBuild project
        build_image = codebuild.Project(
            self,
            "cdk_build",
            project_name=construct_id + "-cdk-build",
            build_spec=codebuild.BuildSpec.from_source_filename("buildspec.yaml"),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
            ),
            role=pipeline_role,
            source=codebuild.Source.code_commit(repository=repository),
            environment_variables={
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(
                    value=target_account or ""
                ),
                "REGION": codebuild.BuildEnvironmentVariable(value=target_region or ""),
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="latest"),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(
                    value=image_repo.repository_name
                ),
                "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(
                    value=image_repo.repository_uri
                ),
                "TASK_DEFINITION_ARN": codebuild.BuildEnvironmentVariable(
                    value=fargate_task_def.task_definition_arn
                ),
                "TASK_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                    value=fargate_task_def.task_role.role_arn
                ),
                "EXECUTION_ROLE_ARN": codebuild.BuildEnvironmentVariable(
                    value=fargate_task_def.execution_role.role_arn
                ),
            },
        )

        # Grant permissions
        existing_bucket.grant_read_write(build_image)
        image_repo.grant_pull_push(build_image)

        # ==================================================
        # =============== CodePipeline ======================
        # ==================================================

        # Create CodePipeline
        pipeline = codepipeline.Pipeline(
            self,
            "pipeline",
            pipeline_name=construct_id,
            role=pipeline_role,
            artifact_bucket=existing_bucket,
            cross_account_keys=True,
        )

        # Create pipeline artifacts
        source_artifact = codepipeline.Artifact("SourceArtifact")
        build_artifact = codepipeline.Artifact("BuildArtifact")

        # Add source stage to pipeline
        source_stage = pipeline.add_stage(stage_name="Source")

        source_action = pipelineactions.CodeCommitSourceAction(
            action_name="CodeCommit_Source",
            branch="main",
            output=source_artifact,
            repository=repository,
            # trigger=pipelineactions.CodeCommitTrigger.POLL,
        )
        source_stage.add_action(source_action)

        # Add build stage to pipeline
        pipeline.add_stage(
            stage_name="Build",
            actions=[
                pipelineactions.CodeBuildAction(
                    action_name="DockerBuildPush",
                    input=source_artifact,
                    project=build_image,
                    role=pipeline_role,
                    outputs=[build_artifact],
                )
            ],
        )

        # ==================================================
        # ============== CodeDeploy Deployment =============
        # ==================================================

        # Create CodeDeploy Deployment Group
        deployment_group = codedeploy.EcsDeploymentGroup(
            self,
            "CodeDeployGroup",
            service=fargate_service,
            blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
                listener=alb_listener,
                blue_target_group=target_group_blue,
                green_target_group=target_group_green,
            ),
        )

        # Add deploy stage to pipeline
        deploy_stage = pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                pipelineactions.CodeDeployEcsDeployAction(
                    action_name="EcsFargateDeploy",
                    app_spec_template_input=build_artifact,
                    task_definition_template_input=build_artifact,
                    deployment_group=deployment_group,
                )
            ],
        )

        # Output ALB endpoint
        CfnOutput(
            self,
            "PublicAlbEndpoint",
            value=f"http://{public_alb.load_balancer_dns_name}",
        )
