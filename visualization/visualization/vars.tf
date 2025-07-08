variable "AWS_ACCESS_KEY" {}
variable "AWS_SECRET_KEY" {}
variable "AWS_REGION" {
  default = "ap-northeast-1"
}

variable "PATH_TO_PRIVATE_KEY" {
  default = "~/.ssh/id_rsa"
}
variable "PATH_TO_PUBLIC_KEY" {
  default = "~/.ssh/id_rsa.pub"
}
variable "INSTANCE_USERNAME" {
  default = "ec2-user"
}

variable "AMIS" {
  default = {
    ap-northeast-1 = "ami-03598bf9d15814511"
  }
} 
