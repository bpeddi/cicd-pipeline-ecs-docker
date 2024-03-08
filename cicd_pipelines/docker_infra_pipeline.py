
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
    aws_lambda as lambda_,
    custom_resources as custom,
    CfnOutput,
    Stack,
    aws_s3 as s3,
    SecretValue,
)
from constructs import Construct
import os


class DockerInfraPipeline(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, env=kwargs['env'])
        target_account = kwargs['target_account']
        target_region = kwargs['target_region']
        env_name = kwargs['env_name']
        repo_name = kwargs['repo_name']
        branch = kwargs['branch']
        cluster_vpc = kwargs['vpccluster_vpc_id']
        artifacts_bucket = kwargs['artifacts_bucket']

      
        



        # artifacts_bucket_name = f'{construct_id}-devops-artifacts-bucket'
        # artifacts_bucket = s3.Bucket(self, 'artifacts_bucket',
        #                              bucket_name=artifacts_bucket_name,
        #                              block_public_access=s3.
        #                              BlockPublicAccess.BLOCK_ALL,
        #                              versioned=False)
        existing_bucket = s3.Bucket.from_bucket_name(self, "ExistingBucket", artifacts_bucket)

        # Creating IAM role for the pipeline
        pipeline_role = iam.Role(self, 'pipeline_role',
                                 assumed_by=iam.CompositePrincipal(
                                     iam.ServicePrincipal("codepipeline.amazonaws.com"),
                                     iam.ServicePrincipal("codebuild.amazonaws.com"),
                                     iam.ServicePrincipal("cloudformation.amazonaws.com")
                                 ),
                                 role_name=construct_id + '-role'
                                 )

        # Adding permissions to the pipeline role
        pipeline_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['sts:AssumeRole', 'codestar-connections:UseConnection'],
            resources=['*']
        ))
        # Creates an Elastic Container Registry (ECR) image repository
        image_repo = ecr.Repository(self, "ImageRepo")

        # Creates a Task Definition for the ECS Fargate service
        fargate_task_def = ecs.FargateTaskDefinition(self, "FargateTaskDef")
        fargate_task_def.add_container(
            "Container",
            container_name="myweb",
            image=ecs.ContainerImage.from_ecr_repository(image_repo),
            port_mappings=[{"containerPort": 80}]
        )

        
        cluster_vpc = ec2.Vpc.from_lookup(self, "ExistingVpc", vpc_id=cluster_vpc)
     
        # Creates VPC for the ECS Cluster
        # cluster_vpc = ec2.Vpc(
        #     self, "ClusterVpc",
        #     ip_addresses=ec2.IpAddresses.cidr(cidr_block="10.75.0.0/16")
        # )

        # Deploys the cluster VPC after the initial image build triggers
        # cluster_vpc.node.add_dependency(trigger_lambda)

        # Creates a new blue Target Group that routes traffic from the public Application Load Balancer (ALB) to the
        # registered targets within the Target Group e.g. (EC2 instances, IP addresses, Lambda functions)
        # https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
        target_group_blue = elb.ApplicationTargetGroup(
            self, "BlueTargetGroup",
            target_group_name="alb-blue-tg",
            target_type=elb.TargetType.IP,
            port=80,
            vpc=cluster_vpc
        )

        # Creates a new green Target Group
        target_group_green = elb.ApplicationTargetGroup(
            self, "GreenTargetGroup",
            target_group_name="alb-green-tg",
            target_type=elb.TargetType.IP,
            port=80,
            vpc=cluster_vpc
        )

        # Creates a Security Group for the Application Load Balancer (ALB)
        albSg = ec2.SecurityGroup(
            self, "AlbSecurityGroup",
            vpc=cluster_vpc,
            allow_all_outbound=True
        )
        albSg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allows access on port 80/http",
            remote_rule=False
        )

        # Creates a public ALB
        public_alb = elb.ApplicationLoadBalancer(
            self, "PublicAlb",
            vpc=cluster_vpc,
            internet_facing=True,
            security_group=albSg
        )

        # Adds a listener on port 80 to the ALB
        alb_listener = public_alb.add_listener(
            "AlbListener80",
            open=False,
            port=80,
            default_target_groups=[target_group_blue]
        )

        # Creates an ECS Fargate service
        # fargate_service = ecs.FargateService(
        #     self, "FargateService",
        #     desired_count=1,
        #     service_name="fargate-frontend-service",
        #     task_definition=fargate_task_def,
        #     cluster=ecs.Cluster(
        #         self, "EcsCluster",
        #         enable_fargate_capacity_providers=True,
        #         vpc=cluster_vpc
        #     ),
        #     # Sets CodeDeploy as the deployment controller
        #     deployment_controller=ecs.DeploymentController(
        #         type=ecs.DeploymentControllerType.CODE_DEPLOY
        #     ),
        # )

        # # Adds the ECS Fargate service to the ALB target group
        # fargate_service.attach_to_application_target_group(target_group_blue)


        # Creates the source stage for CodePipeline
        # source_stage = pipeline.StageProps(
        #     stage_name="Source",
        #     actions=[
        #         pipelineactions.CodeCommitSourceAction(
        #             action_name="CodeCommit",
        #             branch="main",
        #             output=source_artifact,
        #             repository=code_repo
        #         )
        #     ]
        # )



        build_image = codebuild.PipelineProject(self, 'cdk_build',
                                              project_name=construct_id + '-cdk-build',
                                              build_spec=codebuild.BuildSpec.from_source_filename('buildspec.yml'),
                                              environment=codebuild.BuildEnvironment(
                                                  build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                                              ),
                                              role=pipeline_role,
                                            #   source=codebuild.Source.git_hub(
                                            #       owner='bpeddi',
                                            #       repo='myapp',
                                            #       branch_or_ref='main',
                                            #       webhook=True,
                                            #     #   oauth_token=SecretValue.secrets_manager('OAuthSecret'),
                                            #   ),
                                              environment_variables={
                                                        "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=target_account or ""),
                                                        "REGION": codebuild.BuildEnvironmentVariable(value=target_region or ""),
                                                        "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="latest"),
                                                        "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(value=image_repo.repository_name),
                                                        "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=image_repo.repository_uri),
                                                        "TASK_DEFINITION_ARN": codebuild.BuildEnvironmentVariable(value=fargate_task_def.task_definition_arn),
                                                        "TASK_ROLE_ARN": codebuild.BuildEnvironmentVariable(value=fargate_task_def.task_role.role_arn),
                                                        "EXECUTION_ROLE_ARN": codebuild.BuildEnvironmentVariable(value=fargate_task_def.execution_role.role_arn)
                                                    }
                                                    )
        

        
        # pipeline_role.grant(existing_bucket)
        existing_bucket.grant_read_write(build_image)
        # image_repo.grant_pull_push(build_image)
    
        # # Creating CodePipeline add source stage 
        # pipeline = codepipeline.Pipeline(self, 'pipeline',
        #                                  pipeline_name=construct_id,
        #                                  role=pipeline_role,
        #                                  artifact_bucket=artifacts_bucket,
        #                                  cross_account_keys=True,
        #                                  )
        
        # # Creates new pipeline artifacts
        # source_artifact = codepipeline.Artifact("SourceArtifact")
        # build_artifact = codepipeline.Artifact("BuildArtifact")

        # source_stage = pipeline.add_stage(stage_name='Source')
        # source_output = codepipeline.Artifact()
        # source_action = pipelineactions.GitHubSourceAction(
        #     action_name='GitHub_Source',
        #     output=source_artifact,
        #     oauth_token=SecretValue.secrets_manager('OAuthSecret'),
        #     owner='bpeddi',
        #     repo='mymlproject',
        #     branch='main',
        #     trigger=pipelineactions.GitHubTrigger.POLL
        # )
        # source_stage.add_action(source_action)

        # # pipeline.add_stage(
        # #     stage_name='Build',
        # #     actions=[
        # #         pipelineactions.CodeBuildAction(
        # #             input=source_output,
        # #             project=cdk_build,
        # #             role=pipeline_role,
        # #             action_name='cdk_build',
        # #             outputs=[codepipeline.Artifact(artifact_name='BuildOutput')],
        # #             environment_variables={
        # #                 "target_account": codebuild.BuildEnvironmentVariable(value=target_account),
        # #                 "target_region": codebuild.BuildEnvironmentVariable(value=target_region),
        # #                 "env_name": codebuild.BuildEnvironmentVariable(value=env_name),
        # #                 "rprefix": codebuild.BuildEnvironmentVariable(value=rprefix),
        # #                 "vpc_id": codebuild.BuildEnvironmentVariable(value=vpc_id),
        # #                 "private_subnets": codebuild.BuildEnvironmentVariable(value=private_subnets),
        # #             }
        # #         ),
        # #     ]
        # # )

        # # Creates the build stage for CodePipeline
        # pipeline.add_stage(
        #     stage_name="Build",
        #     actions=[
        #         pipelineactions.CodeBuildAction(
        #             action_name="DockerBuildPush",
        #             input=codepipeline.Artifact(),
        #             project=build_image,
        #             outputs=[build_artifact],
        #             role=pipeline_role,
        #         )
        #     ]
        # )

        # # Creates a new CodeDeploy Deployment Group
        # deployment_group = codedeploy.EcsDeploymentGroup(
        #     self, "CodeDeployGroup",
        #     service=fargate_service,
        #     # Configurations for CodeDeploy Blue/Green deployments
        #     blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
        #         listener=alb_listener,
        #         blue_target_group=target_group_blue,
        #         green_target_group=target_group_green
        #     )
        # )

        # # Creates the deploy stage for CodePipeline
        # deploy_stage = pipeline.add_stage(
        #     stage_name="Deploy",
        #     actions=[
        #         pipelineactions.CodeDeployEcsDeployAction(
        #             action_name="EcsFargateDeploy",
        #             app_spec_template_input=build_artifact,
        #             task_definition_template_input=build_artifact,
        #             deployment_group=deployment_group
        #         )
        #     ]
        # )

        # # Creates an AWS CodePipeline with source, build, and deploy stages
        # # pipeline.Pipeline(
        # #     self, "BuildDeployPipeline",
        # #     pipeline_name="ImageBuildDeployPipeline",
        # #     stages=[source_stage, build_stage, deploy_stage]
        # # )

        # Outputs the ALB public endpoint
        CfnOutput(
            self, "PublicAlbEndpoint",
            value=f"http://{public_alb.load_balancer_dns_name}"
        )



        # # Extracting required parameters from kwargs
        # target_account, target_region, env_name, repo_name, branch, rprefix, private_subnets, vpc_id = (
        #     kwargs[k] for k in ("target_account", "target_region", "env_name", "repo_name", "branch", "rprefix", "private_subnets", "vpc_id"))

        # # Creating S3 artifacts bucket
        # artifacts_bucket_name = f'{rprefix}-devops-artifacts-bucket'
        # artifacts_bucket = s3.Bucket(self, 'artifacts_bucket',
        #                              bucket_name=artifacts_bucket_name,
        #                              block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        #                              versioned=False)

        # # Creating IAM role for the pipeline
        # pipeline_role = iam.Role(self, 'pipeline_role',
        #                          assumed_by=iam.CompositePrincipal(
        #                              iam.ServicePrincipal("codepipeline.amazonaws.com"),
        #                              iam.ServicePrincipal("codebuild.amazonaws.com"),
        #                              iam.ServicePrincipal("cloudformation.amazonaws.com")
        #                          ),
        #                          role_name=construct_id + '-role'
        #                          )

        # # Adding permissions to the pipeline role
        # pipeline_role.add_to_policy(iam.PolicyStatement(
        #     effect=iam.Effect.ALLOW,
        #     actions=['sts:AssumeRole', 'codestar-connections:UseConnection'],
        #     resources=['*']
        # ))

        # # Creating CodeBuild projects
        # cdk_build = codebuild.PipelineProject(self, 'cdk_build',
        #                                       project_name=construct_id + '-cdk-build',
        #                                       build_spec=codebuild.BuildSpec.from_source_filename('cdk-build-buildspec.yml'),
        #                                       environment=codebuild.BuildEnvironment(
        #                                           build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
        #                                       ),
        #                                       role=pipeline_role
        #                                       )

        # cdk_deploy = codebuild.PipelineProject(self, 'cdk_deploy',
        #                                        project_name=construct_id + '-cdk-deploy',
        #                                        build_spec=codebuild.BuildSpec.from_source_filename('cdk-deploy-buildspec.yml'),
        #                                        environment=codebuild.BuildEnvironment(
        #                                            build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
        #                                        ),
        #                                        role=pipeline_role
        #                                        )

        # # Creating CodeCommit repository
        # repository = codecommit.Repository.from_repository_name(self, 'repository', repository_name=repo_name)


        # # Creating CodePipeline
        # pipeline = codepipeline.Pipeline(self, 'pipeline',
        #                                  pipeline_name=construct_id,
        #                                  role=pipeline_role,
        #                                  artifact_bucket=artifacts_bucket,
        #                                  cross_account_keys=True,
        #                                  )

        # # Adding source stage to the pipeline
        # source_stage = pipeline.add_stage(stage_name='Source')
        # source_output = codepipeline.Artifact()
        # source_action = codepipeline_actions.GitHubSourceAction(
        #     action_name='GitHub_Source',
        #     output=source_output,
        #     oauth_token=SecretValue.secrets_manager('OAuthSecret'),
        #     owner='bpeddi',
        #     repo='mymlproject',
        #     branch='main',
        #     trigger=codepipeline_actions.GitHubTrigger.POLL
        # )
        # source_stage.add_action(source_action)

        # # Adding build stage to the pipeline
        # pipeline.add_stage(
        #     stage_name='Build',
        #     actions=[
        #         codepipeline_actions.CodeBuildAction(
        #             input=source_output,
        #             project=cdk_build,
        #             role=pipeline_role,
        #             action_name='cdk_build',
        #             outputs=[codepipeline.Artifact(artifact_name='BuildOutput')],
        #             environment_variables={
        #                 "target_account": codebuild.BuildEnvironmentVariable(value=target_account),
        #                 "target_region": codebuild.BuildEnvironmentVariable(value=target_region),
        #                 "env_name": codebuild.BuildEnvironmentVariable(value=env_name),
        #                 "rprefix": codebuild.BuildEnvironmentVariable(value=rprefix),
        #                 "vpc_id": codebuild.BuildEnvironmentVariable(value=vpc_id),
        #                 "private_subnets": codebuild.BuildEnvironmentVariable(value=private_subnets),
        #             }
        #         ),
        #     ]
        # )

        # # Adding manual approval stage for prod environment
        # if env_name in ["prod"]:
        #     pipeline.add_stage(
        #         stage_name="ManualApproval",
        #         actions=[
        #             codepipeline_actions.ManualApprovalAction(
        #                 action_name="RequireApprovalforProd",
        #                 role=pipeline_role,
        #                 additional_information="Review code at " + branch + " branch of repository : " + repo_name,
        #             )]
        #     )

        # # Adding deploy stage to the pipeline
        # pipeline.add_stage(
        #     stage_name="Deploy",
        #     actions=[
        #         codepipeline_actions.CodeBuildAction(
        #             input=source_output,
        #             extra_inputs=[codepipeline.Artifact(artifact_name='BuildOutput')],
        #             project=cdk_deploy,
        #             role=pipeline_role,
        #             action_name='cdk_deploy',
        #             environment_variables={
        #                 "target_account": codebuild.BuildEnvironmentVariable(value=target_account),
        #                 "target_region": codebuild.BuildEnvironmentVariable(value=target_region),
        #                 "env_name": codebuild.BuildEnvironmentVariable(value=env_name),
        #                 "rprefix": codebuild.BuildEnvironmentVariable(value=rprefix),
        #                 "vpc_id": codebuild.BuildEnvironmentVariable(value=vpc_id),
        #                 "private_subnets": codebuild.BuildEnvironmentVariable(value=private_subnets),
        #             }
        #         ),
        #     ]
        # )
       # Creates an AWS CodeCommit repository
        # Adding source stage to the pipeline



        # # CodeBuild project that builds the Docker image
        # build_image = codebuild.Project(
        #     self, "BuildImage",
        #     build_spec=codebuild.BuildSpec.from_source_filename(
        #         "buildspec.yaml"),
        #     source=codebuild.Source.git_hub (  
        #         owner='bpeddi'
        #         repository='mymlproject',
        #         branch_or_ref="main",
        #         oauth_token=SecretValue.secrets_manager('OAuthSecret'),
        #         trigger=codebuild.SourceTrigger.POLL,
        #     )
        #     role=pipeline_role,
        #     environment=codebuild.BuildEnvironment(
        #         privileged=True
        #     ),
        #     environment_variables={
        #         "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=os.getenv('CDK_DEFAULT_ACCOUNT') or ""),
        #         "REGION": codebuild.BuildEnvironmentVariable(value=os.getenv('CDK_DEFAULT_REGION') or ""),
        #         "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value="latest"),
        #         "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(value=image_repo.repository_name),
        #         "REPOSITORY_URI": codebuild.BuildEnvironmentVariable(value=image_repo.repository_uri),
        #         "TASK_DEFINITION_ARN": codebuild.BuildEnvironmentVariable(value=fargate_task_def.task_definition_arn),
        #         "TASK_ROLE_ARN": codebuild.BuildEnvironmentVariable(value=fargate_task_def.task_role.role_arn),
        #         "EXECUTION_ROLE_ARN": codebuild.BuildEnvironmentVariable(value=fargate_task_def.execution_role.role_arn)
        #     }
        # )

        # Grants CodeBuild project access to pull/push images from/to ECR repo

           # # Lambda function that triggers CodeBuild image build project
        # trigger_code_build = lambda_.Function(
        #     self, "BuildLambda",
        #     architecture=lambda_.Architecture.ARM_64,
        #     code=lambda_.Code.from_asset("lambda"),
        #     handler="trigger-build.handler",
        #     runtime=lambda_.Runtime.NODEJS_18_X,
        #     environment={
        #         "CODEBUILD_PROJECT_NAME": build_image.project_name,
        #         "REGION": os.getenv('CDK_DEFAULT_REGION') or ""
        #     },
        #     # Allows this Lambda function to trigger the buildImage CodeBuild project
        #     initial_policy=[
        #         iam.PolicyStatement(
        #             effect=iam.Effect.ALLOW,
        #             actions=["codebuild:StartBuild"],
        #             resources=[build_image.project_arn]
        #         )
        #     ]
        # )

        # # Triggers a Lambda function using AWS SDK
        # trigger_lambda = custom.AwsCustomResource(
        #     self, "BuildLambdaTrigger",
        #     install_latest_aws_sdk=True,
        #     policy=custom.AwsCustomResourcePolicy.from_statements([
        #         iam.PolicyStatement(
        #             effect=iam.Effect.ALLOW,
        #             actions=["lambda:InvokeFunction"],
        #             resources=[trigger_code_build.function_arn],
        #         )
        #     ]),
        #     on_create={
        #         "service": "Lambda",
        #         "action": "invoke",
        #         "physical_resource_id": custom.PhysicalResourceId.of("id"),
        #         "parameters": {
        #             "FunctionName": trigger_code_build.function_name,
        #             "InvocationType": "Event",
        #         },
        #     },
        #     on_update={
        #         "service": "Lambda",
        #         "action": "invoke",
        #         "parameters": {
        #             "FunctionName": trigger_code_build.function_name,
        #             "InvocationType": "Event",
        #         },
        #     }
        # )
