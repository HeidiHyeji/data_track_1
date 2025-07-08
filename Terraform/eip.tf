# s1, s2, s3 EIP
resource "aws_eip" "vm_eip" {
  count  = var.instance_count
  domain = "vpc"
  tags = {
    Name = format("vm_eip_%d", count.index + 1)
  }
}

resource "aws_eip_association" "eip_assoc" {
  count         = var.instance_count
  instance_id   = aws_instance.s[count.index].id
  allocation_id = aws_eip.vm_eip[count.index].id
}

# 모니터링 EIP
resource "aws_eip" "monitoring_eip" {
  domain = "vpc"
  tags = {
    Name = "vm_eip_monitoring"
  }
}

resource "aws_eip_association" "monitoring_eip_assoc" {
  instance_id   = aws_instance.monitoring.id
  allocation_id = aws_eip.monitoring_eip.id
}