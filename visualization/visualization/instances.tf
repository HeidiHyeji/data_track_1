resource "aws_key_pair" "monitoring_key" {
  key_name   = "monitoring_key"
  public_key = file(var.PATH_TO_PUBLIC_KEY)
  lifecycle {
    ignore_changes = [tags]
  }
}

resource "aws_instance" "monitoring" {
  ami           = lookup(var.AMIS, var.AWS_REGION)
  instance_type = "t2.large"
  key_name      = aws_key_pair.monitoring_key.key_name
  vpc_security_group_ids = [aws_security_group.allow_monitoring.id]
  root_block_device{
    volume_size   = 30
  }
  
  provisioner "file" {
    source      = "script.sh"
    destination = "/tmp/script.sh"
  }
  provisioner "remote-exec" {
    inline = [
      "chmod +x /tmp/script.sh",
      "sudo /tmp/script.sh"
    ]
  }
  connection {
    host        = coalesce(self.public_ip, self.private_ip)
    user        = var.INSTANCE_USERNAME
    private_key = file(var.PATH_TO_PRIVATE_KEY)
  }

  tags = {
    Name        = "m1"
  }
}
