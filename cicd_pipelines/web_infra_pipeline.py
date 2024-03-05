from aws_cdk import (
    # Duration,
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_iam as iam,
    aws_kms as kms,
    aws_s3 as s3,
    aws_ssm as ssm,
    SecretValue,
    aws_secretsmanager as secrets
)
from constructs import Construct
import configs.globalconfig as g



class webInfraPipeline(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, env=kwargs['env'])

        # for k, v in kwargs.items():
        #     print(k, v)
        target_account, target_region, env_name, repo_name, branch, rprefix, private_subnets, vpc_id = (kwargs[k] for k in 
            ("target_account","target_region","env_name","repo_name","branch","rprefix","private_subnets","vpc_id"))

        artifacts_bucket_name = f'{rprefix}-devops-artifacts-bucket'  
        artifacts_bucket = s3.Bucket(self, 'artifacts_bucket', 
                        bucket_name=artifacts_bucket_name,
                        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
                        versioned=True
                        )

        

        # artifacts_bucket = s3.Bucket.from_bucket_attributes(self, 'artifacts_bucket', 
        #     bucket_name=artifacts_bucket_name,       
        # )

        ## CI/CD pipeline role

        pipeline_role = iam.Role(self, 'pipeline_role',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("codepipeline.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
                iam.ServicePrincipal("cloudformation.amazonaws.com")
            ),
            role_name=construct_id+'-role'    
        )
        ## CDK Bootstrap roles
        pipeline_role.add_to_policy(iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=['sts:AssumeRole'],
            resources=[
                'arn:aws:iam::*:*',
            ]
        ))

        cdk_build = codebuild.PipelineProject(self, 'cdk_build',
            project_name=construct_id+'-cdk-build',
            build_spec=codebuild.BuildSpec.from_source_filename('cdk-build-buildspec.yml'),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
            ),
            role=pipeline_role,        
        )
        cdk_deploy = codebuild.PipelineProject(self, 'cdk_deploy',
            project_name=construct_id+'-cdk-deploy',
            build_spec=codebuild.BuildSpec.from_source_filename('cdk-deploy-buildspec.yml'),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
            ),
            role=pipeline_role,        
        )

        source_output = codepipeline.Artifact()

        repository = codecommit.Repository.from_repository_name(self, 'repository', repository_name=repo_name)
        
        secret = secrets.Secret(self, "OAuthSecret")
        secret.secret_value.plain_text("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")
        source_output = codepipeline.Artifact(artifact_name='Source')
        build_output = codepipeline.Artifact(artifact_name='BuildOutput')

        # source_action = codepipeline_actions.GitHubSourceAction(
        #     action_name='GitHub_Source',
        #     output=codepipeline.Artifact(),
        #     oauth_token=SecretValue.secrets_manager('OAuthSecret'),
        #     owner='bpeddi',
        #     branch=branch,
        #     repo='mymlproject',
        #     trigger=codepipeline_actions.GitHubTrigger.POLL
        # )
        pipeline = codepipeline.Pipeline(self, 'pipeline',
            pipeline_name=construct_id,
            role=pipeline_role,
            artifact_bucket=artifacts_bucket,
            cross_account_keys=True,
        )
                #  codepipeline_actions.GitHubSourceAction(
                #     action_name='GitHub_Source',
                #     output=codepipeline.Artifact(),
                #     oauth_token=SecretValue.secrets_manager('OAuthSecret'),
                #     owner='bpeddi',
                #     branch="main",
                #     repo='mymlproject',
                #     trigger=codepipeline_actions.GitHubTrigger.POLL
                # )
                    # codepipeline_actions.GitHubSourceAction(
                    # repository=repository,
                    # branch=branch,
                    # role=pipeline_role,
                    # output=source_output,
                    # action_name="GithubSource"
                    # )  
        # pipeline.add_stage(
        #     stage_name='Source',
        #     actions=[
        #         source_action
        #     ]
        # )
        source_stage = pipeline.add_stage(stage_name='Source')
        source_output = codepipeline.Artifact()
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name='GitHub_Source',
            output=source_output,
            oauth_token=SecretValue.secrets_manager('OAuthSecret30537210-GyhCmjuFHrPr'),
            owner='bpeddi',
            repo='mymlproject',
            branch='main',
            trigger=codepipeline_actions.GitHubTrigger.POLL
        )
        source_stage.add_action(source_action)
        pipeline.add_stage(
            stage_name='Build',
            actions=[
                codepipeline_actions.CodeBuildAction(
                    input=source_output,
                    project=cdk_build,
                    role=pipeline_role,
                    action_name='cdk_build',
                    outputs=[build_output],
                    environment_variables={                        
                        "target_account": codebuild.BuildEnvironmentVariable(value=target_account),
                        "target_region": codebuild.BuildEnvironmentVariable(value=target_region),
                        "env_name": codebuild.BuildEnvironmentVariable(value=env_name),
                        "rprefix": codebuild.BuildEnvironmentVariable(value=rprefix),
                        "vpc_id": codebuild.BuildEnvironmentVariable(value=vpc_id),
                        "private_subnets": codebuild.BuildEnvironmentVariable(value=private_subnets),
                        }
                ),
            ]
        )

        pipeline.add_stage(
                stage_name="ManualApproval",
                actions=[
                    codepipeline_actions.ManualApprovalAction(
                    action_name="RequireApprovalforProd",
                    role=pipeline_role,
                    additional_information="Review code at "+branch+" branch of repository : "+repo_name,
                    ## tbd sns, email
                )]

        
        pipeline.add_stage(
            stage_name="Deploy",
            actions=[
                codepipeline_actions.CodeBuildAction(
                    input=source_output,
                    extra_inputs=[build_output],
                    project=cdk_deploy,
                    role=pipeline_role,
                    action_name='cdk_deploy',
                    environment_variables={                        
                        "target_account": codebuild.BuildEnvironmentVariable(value=target_account),
                        "target_region": codebuild.BuildEnvironmentVariable(value=target_region),
                        "env_name": codebuild.BuildEnvironmentVariable(value=env_name),
                        "rprefix": codebuild.BuildEnvironmentVariable(value=rprefix),
                        "ssmpath": codebuild.BuildEnvironmentVariable(value=ssmpath),
                        "vpc_id": codebuild.BuildEnvironmentVariable(value=vpc_id),
                        "private_subnets": codebuild.BuildEnvironmentVariable(value=private_subnets),
                        "database_subnets": codebuild.BuildEnvironmentVariable(value=database_subnets),
                        "glue_service_role_prefix": codebuild.BuildEnvironmentVariable(value=glue_service_role_prefix),
                        "datalake_account": codebuild.BuildEnvironmentVariable(value=datalake_account)
                        }
                ),
            ]
        )


        



        





