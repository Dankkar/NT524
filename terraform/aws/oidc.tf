# --- AWS DATA SOURCES ---
# Dynamically fetch AWS Account ID to construct the OIDC Provider ARN
data "aws_caller_identity" "current" {}

# --- TRUST RELATIONSHIP ASSUME ROLE POLICY DOCUMENT ---
# Restricts role assumption only to the designated GitHub repository
# References the existing global OIDC Provider in the AWS Account dynamically

data "aws_iam_policy_document" "github_actions_assume_role" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:*"]
    }
  }
}

# --- IAM ROLE FOR GITHUB ACTIONS ---
# The role GitHub Actions assumes to build, test, and push images to ECR

resource "aws_iam_role" "github_actions" {
  name               = "github-actions-ecr-push-role"
  assume_role_policy = data.aws_iam_policy_document.github_actions_assume_role.json

  tags = {
    Name        = "GitHub Actions OIDC ECR Push Role"
    Environment = "Production"
  }
}

# --- ECR POLICY ATTACHMENT ---
# Attach power user permissions so GitHub Actions can login and push to ECR repositories

resource "aws_iam_role_policy_attachment" "github_actions_ecr" {
  role       = aws_iam_role.github_actions.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryPowerUser"
}

# --- ECR REPOSITORY FOR WAF DOCKER IMAGE ---

resource "aws_ecr_repository" "waf" {
  name                 = "my-waf-nginx"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name        = "WAF Nginx ECR Repository"
    Environment = "Production"
  }
}

# --- IAM ROLE FOR WAF EC2 INSTANCE TO PULL FROM ECR ---

resource "aws_iam_role" "waf_ec2" {
  name = "waf-ec2-ecr-pull-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "waf_ec2_ecr" {
  role       = aws_iam_role.waf_ec2.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}

resource "aws_iam_instance_profile" "waf_ec2" {
  name = "waf-ec2-instance-profile"
  role = aws_iam_role.waf_ec2.name
}
