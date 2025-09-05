# 构建 zxing-cpp 库 (DLL & LIB) 并在 Windows 上使用

本指南提供了一个在 Windows 环境下，使用 Visual Studio 和 CMake 构建 `zxing-cpp` 库的完整流程。最终目标是生成 `zxing.dll` 和 `zxing.lib` 文件，以便在您自己的 C++ 项目中（例如与 OpenCV 和 YOLOv8 集成的计算机视觉应用）进行二维码和条形码的解码。

## 目录

- [先决条件](#先决条件)
- [构建流程](#构建流程)
  - [步骤 1：克隆 zxing-cpp 仓库](#步骤-1克隆-zxing-cpp-仓库)
  - [步骤 2：安装构建依赖 (pkg-config)](#步骤-2安装构建依赖-pkg-config)
  - [步骤 3：使用 CMake 配置项目](#步骤-3使用-cmake-配置项目)
  - [步骤 4：在 Visual Studio 中编译生成](#步骤-4在-visual-studio-中编译生成)
- [验证构建结果](#验证构建结果)
- [下一步：在你的项目中使用 zxing-cpp](#下一步在你的项目中使用-zxing-cpp)
  - [项目配置](#项目配置)
  - [示例代码](#示例代码)
- [故障排除](#故障排除)

## 先决条件

在开始之前，请确保您的系统上已安装以下工具：

1.  **Visual Studio**: 推荐 Visual Studio 2017 或更高版本，并确保已安装 "使用C++的桌面开发" 工作负载。
2.  **CMake**: 一个跨平台的构建工具。可以从 [官网](https://cmake.org/download/) 下载或通过其他方式安装。
    ```powershell
    # 在终端中验证安装
    cmake --version
    ```
3.  **Git**: 用于克隆源代码仓库。可以从 [官网](https://git-scm.com/download/win) 下载。
4.  **Chocolatey**: Windows 的包管理器，用于简化 `pkg-config` 的安装。

## 构建流程

### 步骤 1：克隆 zxing-cpp 仓库

首先，从 GitHub 克隆最新的 `zxing-cpp` 源代码。

打开一个终端（如 PowerShell 或 CMD），并执行以下命令：

```bash
git clone https://github.com/zxing-cpp/zxing-cpp.git
cd zxing-cpp
```

### 步骤 2：安装构建依赖 (pkg-config)

`zxing-cpp` 的 CMake 配置在某些情况下会依赖 `pkg-config` 工具。在 Windows 上，最简单的安装方式是使用 Chocolatey。

1.  **安装 Chocolatey** (如果尚未安装)
    以**管理员身份**打开 PowerShell，然后运行以下命令：
    ```powershell
    Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    ```
    安装完成后，关闭并重新打开管理员 PowerShell，验证安装：
    ```powershell
    choco --version
    ```

2.  **使用 Chocolatey 安装 pkg-config**
    在管理员 PowerShell 中，运行：
    ```powershell
    choco install pkgconfiglite
    ```

3.  **配置环境变量**
    为了让 CMake 能够找到 `pkg-config`，您需要将其路径添加到环境变量中。以下命令会为**当前终端会话**设置该变量。
    ```powershell
    # 注意：路径可能因 pkgconfiglite 版本而异，请根据实际情况调整
    $env:PKG_CONFIG_PATH="C:\ProgramData\chocolatey\lib\pkgconfiglite\tools\pkg-config-lite-0.28-1\bin"
    ```
    > **提示**: 为了永久生效，建议将此路径添加到系统的 `Path` 环境变量中。

### 步骤 3：使用 CMake 配置项目

现在，我们将使用 CMake 来生成 Visual Studio 项目文件 (`.sln`)。

1.  在 `zxing-cpp` 根目录下创建一个 `build` 文件夹，用于存放所有构建生成的文件。
    ```bash
    mkdir build
    cd build
    ```

2.  运行 CMake 配置命令。您需要根据需求选择生成**动态链接库 (DLL)** 还是**静态链接库 (LIB)**。

    *   **选项 A：生成动态链接库 (DLL)** (推荐，更灵活)
        这将生成 `zxing.dll`（运行时需要）和一个 `zxing.lib`（链接时需要）。
        ```powershell
        cmake -A x64 -DBUILD_SHARED_LIBS=ON -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_FLAGS="/utf-8" ..
        ```

    *   **选项 B：生成静态链接库 (LIB)**
        这将只生成一个 `zxing.lib` 文件，所有代码将被编译到您的最终可执行文件中。
        ```powershell
        cmake -A x64 -DCMAKE_CXX_STANDARD=17 -DCMAKE_CXX_FLAGS="/utf-8" ..
        ```
    
    **参数解释:**
    - `-A x64`: 指定为 64 位架构进行构建。
    - `-DBUILD_SHARED_LIBS=ON`: 关键参数，指示 CMake 构建共享库（DLL）。如果省略，默认为静态库。
    - `-DCMAKE_CXX_STANDARD=17`: 指定使用 C++17 标准。
    - `-DCMAKE_CXX_FLAGS="/utf-8"`: 确保源代码以 UTF-8 编码进行处理，避免在某些环境下出现编译警告或错误。
    - `..`: 指向上一级目录（`zxing-cpp` 根目录），即 `CMakeLists.txt` 所在的位置。

    如果一切顺利，`build` 文件夹中现在应该已经生成了 `ZXing.sln` 文件。

### 步骤 4：在 Visual Studio 中编译生成

1.  双击打开 `build` 文件夹中的 `ZXing.sln` 文件，项目将在 Visual Studio 中加载。
2.  在 Visual Studio 顶部工具栏中，选择构建配置，例如 `Release`（用于生产环境）和平台 `x64`。
3.  在 "解决方案资源管理器" 中，右键点击顶层的 "解决方案 'ZXing'"，然后选择 **"生成解决方案"** (或按 `F7`)。
4.  等待编译完成。

## 验证构建结果

编译成功后，您可以在 `build` 目录中找到生成的库文件：

-   如果构建的是**动态库 (DLL)**:
    -   `build\core\Release\zxing.dll` (运行时动态库)
    -   `build\core\Release\zxing.lib` (用于链接的导入库)
-   如果构建的是**静态库 (LIB)**:
    -   `build\core\Release\zxing.lib` (静态库)

至此，您已经成功构建了 `zxing-cpp` 库！

## 下一步：在你的项目中使用 zxing-cpp

现在，您可以将生成的库集成到您自己的 C++ 项目中。

### 项目配置

假设您在 Visual Studio 中创建了一个新的 C++ 控制台应用程序：

1.  **配置头文件目录**:
    - 右键点击您的项目 -> "属性" -> "C/C++" -> "常规"。
    - 在 "附加包含目录" 中，添加 `zxing-cpp` 源代码的 `core\src` 目录的路径。例如: `C:\path\to\zxing-cpp\core\src`。

2.  **配置库文件目录**:
    - 右键点击您的项目 -> "属性" -> "链接器" -> "常规"。
    - 在 "附加库目录" 中，添加您生成 `.lib` 文件的目录。例如: `C:\path\to\zxing-cpp\build\core\Release`。

3.  **配置链接器输入**:
    - 右键点击您的项目 -> "属性" -> "链接器" -> "输入"。
    - 在 "附加依赖项" 中，添加 `zxing.lib`。

4.  **处理 DLL 文件**:
    - 如果您构建的是**动态库**，请确保将 `zxing.dll` 文件复制到您生成的可执行文件 (`.exe`) 所在的目录，或者一个在系统 `PATH` 环境变量中的目录。

### 示例代码

这是一个简单的示例，演示如何使用 `zxing-cpp` 解码一张图片（这里以 OpenCV 的 `cv::Mat` 为例）。

```cpp
#include <iostream>
#include <opencv2/opencv.hpp>
#include "ReadBarcode.h"
#include "TextUtfEncoding.h"

int main() {
    // 1. 加载图像 (需要链接 OpenCV)
    std::string imagePath = "path/to/your/qrcode.png";
    cv::Mat image = cv::imread(imagePath, cv::IMREAD_GRAYSCALE);

    if (image.empty()) {
        std::cerr << "Error: Could not open or find the image!" << std::endl;
        return -1;
    }

    // 2. 准备 zxing-cpp 需要的图像数据
    // 使用 ZXing::ImageView，避免数据拷贝
    ZXing::ImageView imageView{image.data, image.cols, image.rows, ZXing::ImageFormat::Lum};

    // 3. 配置读取选项 (可选)
    ZXing::DecodeHints hints;
    hints.setTryHarder(true);        // 尝试更复杂的解码
    hints.setFormats(ZXing::BarcodeFormat::Any); // 解码任何格式

    // 4. 调用解码函数
    auto results = ZXing::ReadBarcodes(imageView, hints);

    // 5. 处理并打印结果
    if (results.empty()) {
        std::cout << "No barcode found in the image." << std::endl;
    } else {
        std::cout << "Found " << results.size() << " barcode(s):" << std::endl;
        for (const auto& result : results) {
            // 将结果从 UTF8 转换为本地编码以便在控制台正确显示
            std::cout << "  - Format: " << ZXing::ToString(result.format()) << std::endl;
            std::cout << "  - Text:   " << ZXing::TextUtfEncoding::ToUtf8(result.text()) << std::endl;
        }
    }

    return 0;
}
```

## 故障排除

-   **CMake 错误: `Could NOT find PkgConfig`**:
    这表明 CMake 找不到 `pkg-config` 工具。请返回 [步骤 2](#步骤-2安装构建依赖-pkg-config) 并确保：
    1.  `pkgconfiglite` 已通过 Chocolatey 成功安装。
    2.  `PKG_CONFIG_PATH` 环境变量已在您运行 `cmake` 命令的**同一个终端会话**中正确设置，或者已添加到系统环境变量中。
-   **链接器错误 (LNK2019, LNK2001)**:
    - 确保已在项目的链接器设置中正确添加 `zxing.lib`。
    - 确保您的项目和 `zxing-cpp` 库都使用了相同的架构 (例如，都是 x64) 和相同的运行时库 (例如，都是 MD/MDd)。
-   **源码提示输出变量不为常数，修改源代码**
    - 找到 PDFCodewordDecoder.cpp
    - 删除其中constexpr字段，这会解决编译失败的问题
