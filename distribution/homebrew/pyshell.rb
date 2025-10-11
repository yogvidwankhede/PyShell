class Pyshell < Formula
  include Language::Python::Virtualenv

  desc "Feature-rich POSIX-compatible shell implemented in Python"
  homepage "https://github.com/yogvidwankhede/PyShell"
  url "https://files.pythonhosted.org/packages/source/p/pyshell-terminal/pyshell-terminal-1.1.2.tar.gz"
  sha256 "CCB70B577051F581EECB76E8E3BAC94CDE5C3D46C16BBEC0B0DC50A8C884598F"
  license "MIT"

  depends_on "python@3.9"

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.7.0.tar.gz"
    sha256 "YOUR_SHA256_HERE"
  end

  resource "questionary" do
    url "https://files.pythonhosted.org/packages/source/q/questionary/questionary-2.0.1.tar.gz"
    sha256 "YOUR_SHA256_HERE"
  end

  resource "prompt_toolkit" do
    url "https://files.pythonhosted.org/packages/source/p/prompt-toolkit/prompt_toolkit-3.0.48.tar.gz"
    sha256 "YOUR_SHA256_HERE"
  end

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/pyshell", "-c", "echo test"
  end
end