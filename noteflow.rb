class Noteflow < Formula
  include Language::Python::Virtualenv

  desc "NoteFlow is a lightweight, Markdown-based note-taking application with task management capabilities. It provides a clean interface for creating, viewing, and managing notes with support for tasks, images, and code snippets."
  homepage "https://github.com/Xafloc/NoteFlow"
  url "https://github.com/Xafloc/NoteFlow/archive/refs/tags/v0.1.tar.gz"
  sha256 "497752421a3da0947c3032a0ec72a7c5b3805cc57e70a22abf07b59bf167431a"

  depends_on "python@3.9"

  def install
    virtualenv_install_with_resources
  end

  test do
    system "#{bin}/noteflow", "--version"
  end
end
