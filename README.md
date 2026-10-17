# Solr 環境建置

## 1. 下載與安裝 JDK 17

Solr 運行依賴 Java 環境，請確認電腦中已安裝 JDK 17。
* **下載連結**：[Oracle JDK 17 Archive Downloads](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html)
* 請依據您的作業系統下載對應的安裝檔（Windows 請選擇 x64 Installer）並完成安裝。

## 2. 設定系統環境變數

安裝完 Java 後，必須設定環境變數讓 Solr 能夠順利找到執行路徑。

### 設定 `JAVA_HOME` (系統變數)
1. 開啟 Windows 搜尋，輸入並開啟「**編輯系統環境變數**」。
2. 點擊右下角的「**環境變數**」按鈕。
3. 在下方的「**系統變數**」區塊，點擊「**新增**」。
   * **變數名稱**：`JAVA_HOME`
   * **變數值**：設定為您的 JDK 安裝路徑（例如：`C:\Program Files\Java\jdk-17`，請注意路徑**最後不要包含 `\bin`**）。

### 更新 `Path` (使用者/系統變數)
1. 在上方的「**使用者變數**」（或下方的系統變數）區塊中，找到名為 `Path` 的變數，選取後點擊「**編輯**」。
2. 點擊「**新增**」，並輸入：`%JAVA_HOME%\bin`
3. 一路點擊「確定」儲存所有設定。
(註：設定完成後，若有開啟中的終端機/CMD，請務必重新啟動終端機讓變數生效)

## 3. 啟動與關閉 Solr 伺服器

專案內已附.bat，您可以直接點擊或透過終端機執行來快速管理 Solr 伺服器。

* **啟動 Solr**：執行 `start_solr.bat`
  (啟動成功後，可開啟瀏覽器進入 `http://localhost:8983` 查看 Solr 管理後台)
* **關閉 Solr**：執行 `stop_solr.bat`