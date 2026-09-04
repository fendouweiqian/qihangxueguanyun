<template>
  <div class="app-container home">
    <el-row :gutter="20">
      <el-col :sm="24" :lg="12" style="padding-left: 20px">
        <h2>启航学管云</h2>
        <p>
          面向培训机构的学习视频自动化运营平台，支持多租户开通与批量账号托管，自动完成刷课与学习进度维护。
          <br />
          * 机构级租户隔离与权限管理<br />
          * 学员账号安全托管与批量导入<br />
          * 自动化刷课与任务调度<br />
          * 进度可视化与异常告警<br />
          * 数据导出与多维报表<br />
        </p>
        <p><b>当前版本:</b> <span>v1.0.0</span></p>
        <p>
          <el-tag type="danger">内部部署</el-tag>
        </p>
        <p>
          <el-button type="primary" icon="Cloudy" plain @click="goTarget">访问官网</el-button>
        </p>
      </el-col>

      <el-col :sm="24" :lg="12" style="padding-left: 20px">
        <h2>平台能力</h2>
        <p>
          * 视频学习任务计划与执行策略<br />
          * 机构与学员数据隔离与审计<br />
          * 自动登录校验与异常重试<br />
          * 任务执行日志与可追溯记录<br />
          * 多端访问与安全策略配置<br />
        </p>
        <p><b>技术栈:</b> <span>Vue3 / TypeScript / Python</span></p>
        <p>
          <el-tag type="success">稳定可扩展</el-tag>
        </p>
      </el-col>
    </el-row>
    <el-divider />
  </div>
</template>

<script setup name="Index" lang="ts">
const goTarget = () => {
  window.open(window.location.origin, '_blank');
};
</script>

<style lang="scss" scoped>
.home {
  blockquote {
    padding: 10px 20px;
    margin: 0 0 20px;
    font-size: 17.5px;
    border-left: 5px solid #eee;
  }
  hr {
    margin-top: 20px;
    margin-bottom: 20px;
    border: 0;
    border-top: 1px solid #eee;
  }
  .col-item {
    margin-bottom: 20px;
  }

  ul {
    padding: 0;
    margin: 0;
  }

  font-family: 'open sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  font-size: 13px;
  color: #676a6c;
  overflow-x: hidden;

  ul {
    list-style-type: none;
  }

  h4 {
    margin-top: 0px;
  }

  h2 {
    margin-top: 10px;
    font-size: 26px;
    font-weight: 100;
  }

  p {
    margin-top: 10px;

    b {
      font-weight: 700;
    }
  }

  .update-log {
    ol {
      display: block;
      list-style-type: decimal;
      margin-block-start: 1em;
      margin-block-end: 1em;
      margin-inline-start: 0;
      margin-inline-end: 0;
      padding-inline-start: 40px;
    }
  }
}
</style>
