from __future__ import annotations

from pathlib import Path

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_logs as logs,
)
from constructs import Construct


class ClaimsAgentStack(Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        stage: str,
        ollama_base_url: str,
        ollama_model: str,
        langsmith_project: str,
        langsmith_api_key: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        project_root = Path(__file__).resolve().parents[2]
        service_name = f"claims-agent-{stage}"

        common_env = {
            "PYTHONPATH": "/app",
            "OLLAMA_BASE_URL": ollama_base_url,
            "OLLAMA_MODEL": ollama_model,
            "LANGSMITH_TRACING": "true",
            "LANGSMITH_PROJECT": langsmith_project,
            "LANGSMITH_API_KEY": langsmith_api_key,
            "AWS_REGION": self.region,
        }

        vpc = ec2.Vpc(
            self,
            "ClaimsAgentVpc",
            max_azs=2,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                )
            ],
        )

        cluster = ecs.Cluster(self, "ClaimsAgentCluster", vpc=vpc)

        graph_log_group = logs.LogGroup(
            self,
            "ClaimsGraphLogGroup",
            log_group_name=f"/aws/ecs/{service_name}",
            retention=logs.RetentionDays.ONE_WEEK,
            removal_policy=RemovalPolicy.DESTROY,
        )

        image_asset = ecr_assets.DockerImageAsset(
            self,
            "ClaimsAgentImage",
            directory=str(project_root),
        )

        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ClaimsGraphService",
            cluster=cluster,
            cpu=1024,
            desired_count=1,
            memory_limit_mib=2048,
            public_load_balancer=True,
            assign_public_ip=True,
            service_name=service_name,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(image_asset),
                container_port=8000,
                environment=common_env,
                enable_logging=True,
                log_driver=ecs.LogDrivers.aws_logs(
                    stream_prefix="claims-graph",
                    log_group=graph_log_group,
                ),
            ),
        )

        fargate_service.task_definition.task_role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
        )

        lambda_code = lambda_.Code.from_asset(
            str(project_root),
            exclude=[
                "infra/*",
                "tests/*",
                ".git/*",
                ".venv/*",
                "__pycache__/*",
            ],
        )

        lambda_role = iam.Role(
            self,
            "ClaimsNodeLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        node_function_arns: dict[str, str] = {}
        for function_name, handler in {
            "AnalyseEvidenceNode": "app.lambda_handlers.graph_nodes.analyse_evidence_handler",
            "RiskInvestigationNode": "app.lambda_handlers.graph_nodes.risk_investigation_handler",
            "GenerateBriefingNode": "app.lambda_handlers.graph_nodes.generate_briefing_handler",
            "RouteNextActionNode": "app.lambda_handlers.graph_nodes.route_next_action_handler",
        }.items():
            fn = lambda_.Function(
                self,
                function_name,
                function_name=f"{service_name}-{function_name}",
                runtime=lambda_.Runtime.PYTHON_3_11,
                handler=handler,
                code=lambda_code,
                role=lambda_role,
                timeout=Duration.seconds(120),
                memory_size=1024,
                environment={
                    "PYTHONPATH": "/var/task",
                    "OLLAMA_BASE_URL": ollama_base_url,
                    "OLLAMA_MODEL": ollama_model,
                    "LANGSMITH_TRACING": "true",
                    "LANGSMITH_PROJECT": langsmith_project,
                    "LANGSMITH_API_KEY": langsmith_api_key,
                    "AWS_REGION": self.region,
                },
                log_retention=logs.RetentionDays.ONE_WEEK,
            )
            node_function_arns[function_name] = fn.function_arn
            fn.grant_invoke(fargate_service.task_definition.task_role)

        for name, arn in node_function_arns.items():
            CfnOutput(self, f"{name}Arn", value=arn)

        CfnOutput(
            self,
            "ClaimsGraphServiceUrl",
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
        )
        CfnOutput(self, "ClaimsGraphClusterName", value=cluster.cluster_name)

