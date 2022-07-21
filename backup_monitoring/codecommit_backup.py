from aws_cdk import (
    Duration,
    Stack,
    Tags,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codebuild as codebuild,
    aws_codecommit as codecommit,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_kms as kms,
    aws_s3 as s3,
    aws_ssm as ssm,
    aws_sns as sns,
    aws_lambda as _lambda,

)
from constructs import Construct
from cdk_nag import NagSuppressions
import yaml

class CodeCommitBackup(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, env=kwargs['env'])

        # for k, v in kwargs.items():
        #     print(k, v)

        cicd_ssm_path = kwargs["cicd_ssm_path"]
        rprefix = kwargs["rprefix"]

        # import log bucket
        log_bucket = s3.Bucket.from_bucket_name(self,"log_bucket",
            ssm.StringParameter.value_for_string_parameter(
                self, cicd_ssm_path + "log_bucket_name"
            ),
        )

        # Create backup bucket

        codecommit_backup_bucket = s3.Bucket(self, 'codecommit_backup_bucket',
            bucket_name=f'{rprefix}-codecommit-backups-{self.account}',

            # public access block
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,

            # encryption
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,

            # versioning - not required
            versioned=True,

            # s3 access logs
            server_access_logs_bucket=log_bucket,
            server_access_logs_prefix='s3accesslogs/',

            # Lifecycle policy
            # Move to Glacier after 30 days 
            # Delete after 365 days
            lifecycle_rules=[
                s3.LifecycleRule(
                    enabled=True,
                    
                    # Expire after one year
                    expiration=Duration.days(365),
                    noncurrent_version_expiration=Duration.days(365),
                    # transition to Glacier after 30 days
                    transitions=[ 
                        s3.Transition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30),
                        )
                    ],
                    noncurrent_version_transitions=[ 
                        s3.NoncurrentVersionTransition(
                            storage_class=s3.StorageClass.GLACIER,
                            transition_after=Duration.days(30),
                        )
                    ],
                    abort_incomplete_multipart_upload_after=Duration.days(1)
                )
            ],
        )
            # DataClassification Tag
        Tags.of(codecommit_backup_bucket).add("DataClassification", "Private")

        # codebuild project that git clones codecommit and push to s3

        build_role = iam.Role(self, 'build_role',
            assumed_by=iam.CompositePrincipal(
                iam.ServicePrincipal("events.amazonaws.com"),
                iam.ServicePrincipal("codebuild.amazonaws.com"),
            ),
            role_name=construct_id+'-role'    
        )
        



        with open('backup_monitoring/codecommit_backup_buildspec.yml') as f:
            # use safe_load instead load
            build_spec = yaml.safe_load(f)

        build_job = codebuild.Project(self, 'build_job',
            project_name='codecommit-repo-backup',
            build_spec=codebuild.BuildSpec.from_object_to_yaml(build_spec),
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
            ),
            environment_variables={
                'BACKUP_BUCKET': codebuild.BuildEnvironmentVariable(value=codecommit_backup_bucket.bucket_name)
            },
            role=build_role,
        )
        NagSuppressions.add_resource_suppressions(
            build_job,
            suppressions=[
                {
                    "id": "AwsSolutions-CB4",
                    "reason": "By default files are stored in s3 bucket with AES256 encryption",
                }
            ],
            apply_to_children=True,
        )



        ## monitored_branches = ["prod","master","main","stage", "dev" ]

        codecommit_backup_event = events.Rule(self, 'codecommit_backup_event', 
            event_pattern=events.EventPattern(
                source=["aws.codecommit"],
                detail_type=["CodeCommit Repository State Change"],
                detail={
                    "event": ["referenceCreated", "referenceUpdated" ],
                }),
            rule_name='codecommit_backup_event',
        )

        build_event_input = events.RuleTargetInput.from_object({
            "sourceVersion": events.EventField.from_path("$.detail.sourceCommit"),
            "artifactsOverride": {"type": "NO_ARTIFACTS"},
            "environmentVariablesOverride": [
                {
                    "name": 'commitId',
                    "value": events.EventField.from_path('$.detail.commitId'),
                    "type": 'PLAINTEXT',
                },
                {
                    "name": 'repositoryName',
                    "value": events.EventField.from_path('$.detail.repositoryName'),
                    "type": 'PLAINTEXT',
                },
                {
                    "name": 'referenceName',
                    "value": events.EventField.from_path('$.detail.referenceName'),
                    "type": 'PLAINTEXT',
                },
                {
                    "name": 'region',
                    "value": events.EventField.from_path('$.region'),
                    "type": 'PLAINTEXT',
                }
            ],

        })

        codecommit_backup_event.add_target(targets.CodeBuildProject(
            build_job,
            event=build_event_input,
            event_role=build_role,
        ))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=["codebuild:startBuild"],
            resources=[build_job.project_arn]
        ))
        build_role.add_to_policy(iam.PolicyStatement(
            actions=[
                "codecommit:GitPull",
                "codecommit:Get*",
                "codecommit:BatchGetRepositories",
                "codecommit:List*"
                ],
            resources=["*"]
        ))
        codecommit_backup_bucket.grant_read_write(build_role)

        NagSuppressions.add_resource_suppressions(
            build_role,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "Attached policies contain wildcard chars from AWS provided Managed policies, cdk generated policy which are required for the functionality of the role",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Attached policies contain wildcard chars from AWS provided Managed policies, cdk generated policy which are required for the functionality of the role",
                },
            ],
            apply_to_children=True,
        )




        
