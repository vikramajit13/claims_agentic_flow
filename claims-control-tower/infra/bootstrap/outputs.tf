output "github_actions_role_arn" {
  description = "IAM role ARN for GitHub Actions OIDC deployment."
  value       = aws_iam_role.github_actions_deploy.arn
}

output "github_oidc_provider_arn" {
  description = "OIDC provider ARN for GitHub Actions."
  value       = aws_iam_openid_connect_provider.github.arn
}
