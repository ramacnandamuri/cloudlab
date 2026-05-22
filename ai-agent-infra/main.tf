provider "aws" {
  region = "eu-west-2"
}

# VPC
resource "aws_vpc" "ai_vpc" {
  cidr_block = "10.0.0.0/16"
  tags = { Name = "ai-agent-vpc" }
}

# Subnet
resource "aws_subnet" "ai_subnet" {
  vpc_id                  = aws_vpc.ai_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "eu-west-2a"
  map_public_ip_on_launch = true
  tags = { Name = "ai-agent-subnet" }
}

# Internet Gateway
resource "aws_internet_gateway" "ai_igw" {
  vpc_id = aws_vpc.ai_vpc.id
  tags = { Name = "ai-agent-igw" }
}

# Route Table
resource "aws_route_table" "ai_rt" {
  vpc_id = aws_vpc.ai_vpc.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.ai_igw.id
  }
  tags = { Name = "ai-agent-rt" }
}

# Route Table Association
resource "aws_route_table_association" "ai_rta" {
  subnet_id      = aws_subnet.ai_subnet.id
  route_table_id = aws_route_table.ai_rt.id
}

# Security Group
resource "aws_security_group" "ai_sg" {
  vpc_id = aws_vpc.ai_vpc.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "ai-agent-sg" }
}

# IAM Role for EC2
resource "aws_iam_role" "ai_role" {
  name = "ai-agent-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "ai_profile" {
  name = "ai-agent-profile"
  role = aws_iam_role.ai_role.name
}

# EC2 Instance
resource "aws_instance" "ai_agent" {
  ami                    = "ami-0b45ae66668865cd6"
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.ai_subnet.id
  vpc_security_group_ids = [aws_security_group.ai_sg.id]
  iam_instance_profile   = aws_iam_instance_profile.ai_profile.name
  key_name               = "cloudlab-key"   


  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y docker
    systemctl start docker
    systemctl enable docker
    docker pull ramachaitanya/aiops-agent:latest
    docker run -d ramachaitanya/aiops-agent:latest
  EOF

  tags = { Name = "ai-agent-ec2" }
}

# Output
output "ec2_public_ip" {
  value = aws_instance.ai_agent.public_ip
}