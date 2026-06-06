# AWS Deployment

This CDK app provisions:

- a public ECS Fargate service for the main claims graph/API
- one Lambda function per parent graph node
- VPC, ALB, CloudWatch Logs, IAM roles

Target region:

- `ap-southeast-2` (AWS Asia Pacific - Sydney)

## Deployed Components

### ECS Fargate

The Fargate service runs the current FastAPI application container and hosts:

- the workflow API
- the parent claims review graph
- the private risk investigation subgraph

### Lambda Node Functions

The following Lambda functions are packaged from the same codebase:

- `AnalyseEvidenceNode`
- `RiskInvestigationNode`
- `GenerateBriefingNode`
- `RouteNextActionNode`

These functions are intended as node-level building blocks for future decomposition, remote orchestration, or Step Functions integration.

## Deployment Inputs

The CDK app expects:

- AWS account
- region
- Ollama base URL
- Ollama model
- LangSmith project
- LangSmith API key

## Deploy

Use:

```bash
../../scripts/deploy_aws_sydney.sh
```

