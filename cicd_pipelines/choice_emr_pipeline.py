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
    aws_sns as sns,
    aws_events_targets as events_targets,
    aws_events as events,
)
from constructs import Construct
from cdk_nag import NagSuppressions

class ChoiceEmrPipeline(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, env=kwargs['env'])

        # for k, v in kwargs.items():
        #     print(k, v)

        target_account, target_region, env_name, repo_name, branch, rprefix, ssmpath, cicd_ssm_path, private_subnets, database_subnets, vpc_id, glue_service_role_name = (kwargs[k] for k in 
            ("target_account","target_region","env_name","repo_name","branch","rprefix","ssmpath","cicd_ssm_path","private_subnets","database_subnets","vpc_id", "glue_service_role_name"))

        ## Retrieve params from ssm
        artifacts_bucket_name = ssm.StringParameter.from_string_parameter_name(self, 'artifacts_bucket_name', string_parameter_name=cicd_ssm_path+'artifacts_bucket_name').string_value            
        artifacts_key_arn = ssm.StringParameter.from_string_parameter_name(self, 'artifacts_key_arn', string_parameter_name=cicd_ssm_path+'artifacts_key_arn').string_value
        sns_notify_cicd_approvals_arn = ssm.StringParameter.from_string_parameter_name(self, 'sns_notify_cicd_approvals_arn', string_parameter_name=cicd_ssm_path+'sns_notify_cicd_approvals').string_value
        sns_notify_pipeline_status_arn = ssm.StringParameter.from_string_parameter_name(self, 'sns_notify_pipeline_status_arn', string_parameter_name=cicd_ssm_path+'sns_notify_pipeline_status').string_value


        # import resources
        artifacts_key = kms.Key.from_key_arn(self, 'artifacts_key', key_arn=artifacts_key_arn)

        artifacts_bucket = s3.Bucket.from_bucket_attributes(self, 'artifacts_bucket', 
            bucket_name=artifacts_bucket_name,
            encryption_key=artifacts_key,           
        )

        sns_notify_cicd_approvals = sns.Topic.from_topic_arn(self, 'sns_notify_cicd_approvals', sns_notify_cicd_approvals_arn)
        sns_notify_pipeline_status = sns.Topic.from_topic_arn(self, 'sns_notify_pipeline_status', sns_notify_pipeline_status_arn)    
    

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
                'arn:aws:iam::*:role/cdk-hnb659fds-lookup-role-*',
                'arn:aws:iam::*:role/cdk-hnb659fds-deploy-role-*',
                'arn:aws:iam::*:role/cdk-hnb659fds-file-publishing-*',
            ]
        ))
        NagSuppressions.add_resource_suppressions(pipeline_role,
        suppressions=[
            {'id': 'AwsSolutions-IAM5', 'reason' : 'CDK automation adds secure default policies for various actions with wildcards. Cannot be avoided'}
        ],
        apply_to_children=True
        )

        cdk_build = codebuild.PipelineProject(self, 'cdk_build',
            project_name=construct_id+'-cdk-build',
            build_spec=codebuild.BuildSpec.from_source_filename('cdk-build-buildspec.yml'),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
            ),
            encryption_key=artifacts_key,
            role=pipeline_role,        
        )
        cdk_deploy = codebuild.PipelineProject(self, 'cdk_deploy',
            project_name=construct_id+'-cdk-deploy',
            build_spec=codebuild.BuildSpec.from_source_filename('cdk-deploy-buildspec.yml'),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
            ),
            encryption_key=artifacts_key,
            role=pipeline_role,        
        )

        repository = codecommit.Repository.from_repository_name(self, 'repository', repository_name=repo_name)

        source_output = codepipeline.Artifact(artifact_name='Source')
        build_output = codepipeline.Artifact(artifact_name='BuildOutput')

        pipeline = codepipeline.Pipeline(self, 'pipeline',
            pipeline_name=construct_id,
            role=pipeline_role,
            artifact_bucket=artifacts_bucket,
            cross_account_keys=True,
        )

        pipeline.add_stage(
            stage_name='Source',
            actions=[
                codepipeline_actions.CodeCommitSourceAction(
                    repository=repository,
                    branch=branch,
                    role=pipeline_role,
                    output=source_output,
                    action_name="CodecommitSource",
                )
            ]
        )

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
                        "ssmpath": codebuild.BuildEnvironmentVariable(value=ssmpath),
                        "vpc_id": codebuild.BuildEnvironmentVariable(value=vpc_id),
                        "private_subnets": codebuild.BuildEnvironmentVariable(value=private_subnets),
                        "database_subnets": codebuild.BuildEnvironmentVariable(value=database_subnets),
                        "glue_service_role_name": codebuild.BuildEnvironmentVariable(value=glue_service_role_name),
                        
                        }
                ),
            ]
        )

        if env_name in ["dev","prod"]:
            pipeline.add_stage(
                stage_name="ManualApproval",
                actions=[
                    codepipeline_actions.ManualApprovalAction(
                    action_name="RequireApprovalforProd",
                    role=pipeline_role,
                    additional_information="Review code at "+branch+" branch of repository : "+repo_name,
                    #external_entity_link="https://"+self.region+".console.aws.amazon.com/codesuite/codecommit/repositories/#{SourceVariables.RepositoryName}/commit/#{"+"SourceVariables.CommitId}"
                    notification_topic=sns_notify_cicd_approvals
                )]
            )
        
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
                        "glue_service_role_name": codebuild.BuildEnvironmentVariable(value=glue_service_role_name),
                        }
                ),
            ]
        )






        



        





