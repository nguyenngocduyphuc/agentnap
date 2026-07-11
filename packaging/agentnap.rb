class Agentnap < Formula
  desc "App Nap for your AI agents — reclaim the RAM AI coding agents leak"
  homepage "https://github.com/nguyenngocduyphuc/agentnap"
  url "https://github.com/nguyenngocduyphuc/agentnap/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "9917249c62db1b8380133b8dab97cf91d42030d514bbfd8a116f6744aba13c8a"
  license "MIT"

  uses_from_macos "python"

  def install
    bin.install "agentnap.py" => "agentnap"
  end

  test do
    assert_match "agentnap 1.0.0", shell_output("#{bin}/agentnap --version")
  end
end
