# --- ECR REPOSITORY FOR WAF DOCKER IMAGE ---

resource "aws_ecr_repository" "waf" {
  name                 = "my-waf-nginx"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

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
