terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "eu-west-2"
}

resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"

  tags = {
    Name = "cloudlab-vpc"
  }
}
resource "aws_subnet" "public" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = "eu-west-2a"

  tags = {
    Name = "cloudlab-public-subnet"
  }
}
resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "cloudlab-igw"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "cloudlab-rt"
  }
}

resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.igw.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_security_group" "web" {
  name        = "cloudlab-sg"
  description = "CloudLab security group"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cloudlab-sg"
  }
}
resource "aws_instance" "web" {
  ami                         = "ami-01494bc399c17fe43"
  instance_type               = var.instance_type
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.web.id]
  key_name                    = "cloudlab-key"
  associate_public_ip_address = true

  user_data = <<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu       
    docker run -d --restart always --name webapp -p 3000:3000 ${var.webapp_image}  
    EOF

  tags = {
    Name = "cloudlab-ec2"
  }
}

resource "aws_eip" "web" {
  instance = aws_instance.web.id
  domain   = "vpc"

  tags = {
    Name = "cloudlab-eip"
  }
}
resource "aws_subnet" "public2" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "eu-west-2b"

  tags = {
    Name = "cloudlab-public-subnet-2"
  }
}

resource "aws_route_table_association" "public2" {
  subnet_id      = aws_subnet.public2.id
  route_table_id = aws_route_table.public.id
}

# Security group for load balancer
resource "aws_security_group" "alb" {
  name        = "cloudlab-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "cloudlab-alb-sg"
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "cloudlab-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public.id, aws_subnet.public2.id]

  tags = {
    Name = "cloudlab-alb"
  }
}

# Target Group
resource "aws_lb_target_group" "webapp" {
  name     = "cloudlab-tg"
  port     = 3000
  protocol = "HTTP"
  vpc_id   = aws_vpc.main.id

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 2
    interval            = 30
  }

  tags = {
    Name = "cloudlab-tg"
  }
}

# Listener
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.webapp.arn
  }
}

resource "aws_launch_template" "webapp" {
  name_prefix   = "cloudlab-"
  image_id      = var.ami_id
  instance_type = var.instance_type

  key_name = "cloudlab-key"

  network_interfaces {
    associate_public_ip_address = true
    security_groups             = [aws_security_group.web.id]
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    apt-get update -y
    apt-get install -y docker.io
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
    docker run -d --restart always --name webapp -p 3000:3000 ${var.webapp_image}
  EOF
  )

  tags = {
    Name = "cloudlab-lt"
  }
}

resource "aws_autoscaling_group" "webapp" {
  name                = "cloudlab-asg"
  desired_capacity    = 2
  min_size            = 1
  max_size            = 4
  target_group_arns   = [aws_lb_target_group.webapp.arn]
  vpc_zone_identifier = [aws_subnet.public.id, aws_subnet.public2.id]

  launch_template {
    id      = aws_launch_template.webapp.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "cloudlab-asg-instance"
    propagate_at_launch = true
  }
}

# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "cloudlab-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = "ramacnandamuri@gmail.com"
}

# ALB - Unhealthy hosts alarm
resource "aws_cloudwatch_metric_alarm" "unhealthy_hosts" {
  alarm_name          = "cloudlab-unhealthy-hosts"
  alarm_description   = "Alert when healthy host count drops below 1"
  metric_name         = "HealthyHostCount"
  namespace           = "AWS/ApplicationELB"
  statistic           = "Minimum"
  period              = 60
  threshold           = 1
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
    TargetGroup  = aws_lb_target_group.webapp.arn_suffix
  }
}

# ALB - High latency alarm
resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "cloudlab-high-latency"
  alarm_description   = "Alert when response time exceeds 2 seconds"
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  statistic           = "Average"
  period              = 60
  threshold           = 2
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    LoadBalancer = aws_lb.main.arn_suffix
  }
}

# EC2 - High CPU alarm
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "cloudlab-high-cpu"
  alarm_description   = "Alert when CPU exceeds 80%"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  statistic           = "Average"
  period              = 300
  threshold           = 80
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.webapp.name
  }
}
# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "webapp" {
  name              = "/cloudlab/webapp"
  retention_in_days = 7

  tags = {
    Name = "cloudlab-webapp-logs"
  }
}

resource "aws_cloudwatch_log_group" "ec2" {
  name              = "/cloudlab/ec2"
  retention_in_days = 7

  tags = {
    Name = "cloudlab-ec2-logs"
  }
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "cloudlab-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          title  = "CPU Utilisation"
          metrics = [
            ["AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "cloudlab-asg"]
          ]
          period = 300
          stat   = "Average"
          region = "eu-west-2"
        }
      },
      {
        type = "metric"
        properties = {
          title  = "ALB Request Count"
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", aws_lb.main.arn_suffix]
          ]
          period = 300
          stat   = "Sum"
          region = "eu-west-2"
        }
      },
      {
        type = "metric"
        properties = {
          title  = "ALB Response Time"
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", aws_lb.main.arn_suffix]
          ]
          period = 300
          stat   = "Average"
          region = "eu-west-2"
        }
      },
      {
        type = "metric"
        properties = {
          title  = "Healthy Host Count"
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount", "LoadBalancer", aws_lb.main.arn_suffix, "TargetGroup", aws_lb_target_group.webapp.arn_suffix]
          ]
          period = 60
          stat   = "Minimum"
          region = "eu-west-2"
        }
      }
    ]
  })
}