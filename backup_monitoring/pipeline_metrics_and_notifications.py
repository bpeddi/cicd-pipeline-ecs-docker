from aws_cdk import (
    # Duration,
    Duration,
    Stack,
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

class PipelineNotifications(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, env=kwargs['env'])

        # for k, v in kwargs.items():
        #     print(k, v)

        cicd_ssm_path = kwargs["cicd_ssm_path"]

        sns_notify_cicd_approvals_arn = ssm.StringParameter.from_string_parameter_name(self, 'sns_notify_cicd_approvals_arn', string_parameter_name=cicd_ssm_path+'sns_notify_cicd_approvals').string_value
        sns_notify_pipeline_status_arn = ssm.StringParameter.from_string_parameter_name(self, 'sns_notify_pipeline_status_arn', string_parameter_name=cicd_ssm_path+'sns_notify_pipeline_status').string_value

        # import resources
        sns_notify_cicd_approvals = sns.Topic.from_topic_arn(self, 'sns_notify_cicd_approvals', sns_notify_cicd_approvals_arn)
        sns_notify_pipeline_status = sns.Topic.from_topic_arn(self, 'sns_notify_pipeline_status', sns_notify_pipeline_status_arn)                
        
        ## monitored_branches = ["prod","master","main","stage"]

        ## Repository pull request notifications
        pull_request_event_rule = events.Rule(self, 'pull_request_event_rule', 
            event_pattern=events.EventPattern(
                source=["aws.codecommit"],
                detail_type=["CodeCommit Pull Request State Change"],
                detail={
                    "event": ["pullRequestCreated", "pullRequestStatusChanged", "pullRequestApprovalRuleCreated", "pullRequestApprovalStateChanged", "pullRequestApprovalRuleOverridden", "pullRequestApprovalRuleDeleted"],
                    "destinationReference": [ "refs/heads/prod", "refs/heads/master", "refs/heads/main", "refs/heads/stage" ]
                }),
            rule_name='notify-pipeline-pull-requests'
        )
        pull_request_event_rule.add_target(targets.SnsTopic(sns_notify_cicd_approvals))


        handle_pipeline_event = _lambda.Function(
            scope=self,
            id="handle_pipeline_event",
            handler="index.handlePipelineEvent",
            runtime=_lambda.Runtime.NODEJS_14_X  ,
            code=_lambda.Code.from_asset("cloudwatch_dashboard"),
            timeout=Duration.seconds(900),
        )
        handle_pipeline_event.add_to_role_policy(iam.PolicyStatement(
            actions=[ 
                "codepipeline:ListPipelineExecutions",
                "cloudwatch:PutMetricData"
            ],
            resources=["*"]
        ))



        generate_dashboard = _lambda.Function(
            scope=self,
            id="generate_dashboard",
            handler="index.generateDashboard",
            runtime=_lambda.Runtime.NODEJS_14_X  ,
            code=_lambda.Code.from_asset("cloudwatch_dashboard"),
            timeout=Duration.seconds(900),
        )
        generate_dashboard.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "cloudwatch:GetDashboard",
                "cloudwatch:ListDashboards",
                "cloudwatch:PutDashboard",
                "cloudwatch:ListMetrics"
            ],
            resources=["*"]
        ))

        for role in [handle_pipeline_event,generate_dashboard]:
            NagSuppressions.add_resource_suppressions(
                role,
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

        ## Pipeline Execution Events
        pipeline_execution_event = events.Rule(self, 'pipeline_execution_event_rule', 
            event_pattern=events.EventPattern(
                source=["aws.codepipeline"],
                detail_type=["CodePipeline Pipeline Execution State Change", "CodePipeline Stage Execution State Change", "CodePipeline Action Execution State Change"],
                ),
                rule_name='pipeline_execution_event'
        )
        pipeline_execution_event.add_target(targets.LambdaFunction(handle_pipeline_event))

        ## Pipeline Dashboard Scheduled event 
        generate_pipeline_dashboard_schedule = events.Rule(self, 'generate_pipeline_dashboard_schedule', 
            schedule=events.Schedule.rate(Duration.minutes(5)),
            rule_name='generate_pipeline_dashboard_schedule'
        )
        generate_pipeline_dashboard_schedule.add_target(targets.LambdaFunction(generate_dashboard))


        pipeline_stage_failed_event = events.Rule(self, 'pipeline_stage_failed_event', 
            event_pattern=events.EventPattern(
                source=["aws.codepipeline"],
                detail_type=["CodePipeline Stage Execution State Change"],
                detail={
                    "state": ["FAILED", "CANCELED"],
                }),
                rule_name='pipeline_stage_failed_event'
        )
        pipeline_stage_failed_event.add_target(targets.SnsTopic(sns_notify_pipeline_status))
        

        
