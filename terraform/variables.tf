variable "my_ip" {
  description = "Your home IP for SSH access"
  type        = string
default = "0.0.0.0/0"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t4g.micro"
}

variable "webapp_image" {
  description = "Docker image to deploy"
  type        = string
  default     = "ramachaitanya/webapp:latest"
}

variable "ami_id" {
  description = "AMI ID for EC2 instances"
  type        = string
  default     = "ami-01494bc399c17fe43"
}

