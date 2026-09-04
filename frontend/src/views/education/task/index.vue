<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="订单" prop="orderId">
              <el-input v-model="queryParams.orderId" placeholder="请输入订单ID" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="任务类型" prop="taskType">
              <el-input v-model="queryParams.taskType" placeholder="任务类型" clearable style="width: 120px" />
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="queryParams.status" placeholder="状态" clearable style="width: 140px">
                <el-option v-for="item in taskStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
              <el-button icon="Refresh" @click="resetQuery">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </div>
    </transition>

    <el-card shadow="hover">
      <template #header>
        <el-row :gutter="10" class="mb8">
          <el-col :span="1.5">
            <el-button type="primary" plain icon="Plus" @click="handleAdd">新增</el-button>
          </el-col>
          <el-col :span="1.5">
            <el-button type="success" plain icon="Edit" :disabled="single" @click="handleUpdate()">修改</el-button>
          </el-col>
          <el-col :span="1.5">
            <el-button type="warning" plain icon="RefreshRight" :disabled="single" @click="handleRun()">重新入队</el-button>
          </el-col>
          <el-col :span="1.5">
            <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete()">删除</el-button>
          </el-col>
          <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="taskList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="任务ID" align="center" prop="taskId" width="110" />
        <el-table-column label="订单ID" align="center" prop="orderId" width="110" />
        <el-table-column label="类型" align="center" prop="taskType" width="80" />
        <el-table-column label="状态" align="center" width="110">
          <template #default="scope">
            <el-tag :type="taskStatusTag(scope.row.status)">{{ taskStatusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="执行节点" align="center" prop="workerCode" width="180" :show-overflow-tooltip="true" />
        <el-table-column label="触发时间" align="center" prop="triggerAt" width="170" />
        <el-table-column label="开始时间" align="center" prop="startedAt" width="170" />
        <el-table-column label="心跳时间" align="center" prop="heartbeatAt" width="170" />
        <el-table-column label="结束时间" align="center" prop="finishedAt" width="170" />
        <el-table-column label="摘要" align="center" prop="resultSummary" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="错误信息" align="center" prop="lastError" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="180">
          <template #default="scope">
            <el-tooltip content="详情" placement="top">
              <el-button link type="primary" icon="View" @click="handleDetail(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="修改" placement="top">
              <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="重新入队" placement="top">
              <el-button link type="warning" icon="RefreshRight" @click="handleRun(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="danger" icon="Delete" @click="handleDelete(scope.row)"></el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="680px" append-to-body>
      <el-form ref="taskFormRef" :model="form" :rules="rules" label-width="110px">
        <el-form-item label="订单ID" prop="orderId">
          <el-input v-model="form.orderId" placeholder="请输入订单ID" />
        </el-form-item>
        <el-form-item label="任务类型" prop="taskType">
          <el-input-number v-model="form.taskType" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-input-number v-model="form.status" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="触发时间" prop="triggerAt">
          <el-date-picker v-model="form.triggerAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="执行节点" prop="workerCode">
          <el-input v-model="form.workerCode" placeholder="请输入执行节点" />
        </el-form-item>
        <el-form-item label="开始时间" prop="startedAt">
          <el-date-picker v-model="form.startedAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间" prop="finishedAt">
          <el-date-picker v-model="form.finishedAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="心跳时间" prop="heartbeatAt">
          <el-date-picker v-model="form.heartbeatAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="重试次数" prop="retryCount">
          <el-input-number v-model="form.retryCount" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="执行摘要" prop="resultSummary">
          <el-input v-model="form.resultSummary" placeholder="请输入执行摘要" type="textarea" />
        </el-form-item>
        <el-form-item label="错误信息" prop="lastError">
          <el-input v-model="form.lastError" placeholder="请输入错误信息" type="textarea" />
        </el-form-item>
        <el-form-item label="任务配置" prop="taskConfigJson">
          <el-input v-model="form.taskConfigJson" placeholder="请输入任务配置 JSON" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>

    <el-drawer v-model="detailVisible" title="任务详情" size="70%">
      <div v-loading="detailLoading">
        <el-empty v-if="!detail.task" description="暂无详情数据" />
        <template v-else>
          <el-descriptions :column="2" border class="mb-4 task-detail-summary">
            <el-descriptions-item label="任务ID">{{ detail.task.taskId }}</el-descriptions-item>
            <el-descriptions-item label="订单ID">{{ detail.task.orderId }}</el-descriptions-item>
            <el-descriptions-item label="任务状态">
              <el-tag :type="taskStatusTag(detail.task.status)">{{ taskStatusLabel(detail.task.status) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="执行节点">{{ detail.task.workerCode || '-' }}</el-descriptions-item>
            <el-descriptions-item label="触发时间">{{ detail.task.triggerAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ detail.task.startedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="心跳时间">{{ detail.task.heartbeatAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ detail.task.finishedAt || '-' }}</el-descriptions-item>
            <el-descriptions-item label="执行摘要" :span="2">{{ detail.task.resultSummary || '-' }}</el-descriptions-item>
            <el-descriptions-item label="错误信息" :span="2">{{ detail.task.lastError || '-' }}</el-descriptions-item>
          </el-descriptions>

          <el-row :gutter="16" class="mb-4">
            <el-col :span="12">
              <el-card shadow="never" header="课程进度">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="课程">{{ detail.courseProgress?.courseName || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="学期">{{ detail.courseProgress?.term || '-' }}</el-descriptions-item>
                  <el-descriptions-item label="视频">{{
                    progressLabel(detail.courseProgress?.videoStatus, detail.courseProgress?.videoNote)
                  }}</el-descriptions-item>
                  <el-descriptions-item label="作业">{{
                    progressLabel(detail.courseProgress?.workStatus, detail.courseProgress?.workNote)
                  }}</el-descriptions-item>
                  <el-descriptions-item label="考试">{{
                    progressLabel(detail.courseProgress?.examStatus, detail.courseProgress?.examNote)
                  }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never" header="考试进度">
                <el-descriptions :column="1" border>
                  <el-descriptions-item label="状态">{{
                    progressLabel(detail.examProgress?.status, detail.examProgress?.note)
                  }}</el-descriptions-item>
                  <el-descriptions-item label="分数">{{ detail.examProgress?.score ?? '-' }}</el-descriptions-item>
                  <el-descriptions-item label="完成时间">{{ detail.examProgress?.finishedAt || '-' }}</el-descriptions-item>
                </el-descriptions>
              </el-card>
            </el-col>
          </el-row>

          <el-card shadow="never" class="mb-4" header="任务配置">
            <pre class="detail-json">{{ prettyJson(detail.task.taskConfigJson) }}</pre>
          </el-card>

          <el-card shadow="never" class="mb-4" header="运行日志">
            <el-table border :data="detail.logs || []">
              <el-table-column label="序号" align="center" prop="seqNo" width="90" />
              <el-table-column label="级别" align="center" prop="level" width="100" />
              <el-table-column label="节点" align="center" prop="workerCode" width="180" :show-overflow-tooltip="true" />
              <el-table-column label="日志内容" prop="message" min-width="420" :show-overflow-tooltip="true" />
              <el-table-column label="时间" align="center" prop="createdAt" width="180" />
            </el-table>
          </el-card>

          <el-card shadow="never" header="题库失败记录">
            <el-table border :data="detail.tikuFailures || []">
              <el-table-column label="来源" align="center" prop="provider" width="120" />
              <el-table-column label="题目" prop="question" min-width="260" :show-overflow-tooltip="true" />
              <el-table-column label="失败原因" prop="reason" min-width="220" :show-overflow-tooltip="true" />
              <el-table-column label="原始响应" prop="rawResponse" min-width="260" :show-overflow-tooltip="true" />
              <el-table-column label="时间" align="center" prop="createTime" width="180" />
            </el-table>
          </el-card>
        </template>
      </div>
    </el-drawer>
  </div>
</template>

<script setup name="EduTask" lang="ts">
import { addTask, delTask, getTask, getTaskDetail, listTask, runTask, updateTask } from '@/api/education/task';
import { EaTaskDetailVO, EaTaskForm, EaTaskQuery, EaTaskVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const taskList = ref<EaTaskVO[]>([]);
const loading = ref(true);
const detailLoading = ref(false);
const detailVisible = ref(false);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const taskStatusOptions = [
  { label: '待执行', value: 0 },
  { label: '执行中', value: 1 },
  { label: '成功', value: 2 },
  { label: '失败', value: 3 }
];

const queryFormRef = ref<ElFormInstance>();
const taskFormRef = ref<ElFormInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const initFormData: EaTaskForm = {
  taskId: undefined,
  orderId: undefined,
  taskType: 0,
  status: 0,
  triggerAt: '',
  workerCode: '',
  startedAt: '',
  finishedAt: '',
  heartbeatAt: '',
  retryCount: 0,
  lastError: '',
  resultSummary: '',
  taskConfigJson: ''
};

const detail = ref<EaTaskDetailVO>({});

const data = reactive<PageData<EaTaskForm, EaTaskQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    orderId: undefined,
    status: undefined,
    taskType: undefined
  },
  rules: {
    orderId: [{ required: true, message: '订单ID不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const taskStatusLabel = (status?: number) => taskStatusOptions.find((item) => item.value === status)?.label || '未知';

const taskStatusTag = (status?: number) => {
  if (status === 1) {
    return 'warning';
  }
  if (status === 2) {
    return 'success';
  }
  if (status === 3) {
    return 'danger';
  }
  return 'info';
};

const progressLabel = (status?: number, note?: string) => {
  const label = status === 1 ? '已完成' : status === 2 ? '失败' : status === 3 ? '处理中' : '未开始';
  return note ? `${label} / ${note}` : label;
};

const prettyJson = (value?: string) => {
  if (!value) {
    return '-';
  }
  try {
    return JSON.stringify(JSON.parse(value), null, 2);
  } catch {
    return value;
  }
};

const getList = async () => {
  loading.value = true;
  const res = await listTask(queryParams.value);
  taskList.value = res.rows;
  total.value = res.total;
  loading.value = false;
};

const handleQuery = () => {
  queryParams.value.pageNum = 1;
  getList();
};

const resetQuery = () => {
  queryFormRef.value?.resetFields();
  handleQuery();
};

const handleSelectionChange = (selection: EaTaskVO[]) => {
  ids.value = selection.map((item) => item.taskId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const reset = () => {
  form.value = { ...initFormData };
  taskFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = () => {
  reset();
  dialog.visible = true;
  dialog.title = '新增任务';
};

const handleUpdate = async (row?: EaTaskVO) => {
  reset();
  const taskId = row?.taskId || ids.value[0];
  const { data } = await getTask(taskId);
  Object.assign(form.value, data);
  dialog.visible = true;
  dialog.title = '修改任务';
};

const handleDetail = async (row: EaTaskVO) => {
  detailVisible.value = true;
  detailLoading.value = true;
  try {
    const { data } = await getTaskDetail(row.taskId);
    detail.value = data || {};
  } finally {
    detailLoading.value = false;
  }
};

const submitForm = () => {
  taskFormRef.value?.validate(async (valid: boolean) => {
    if (valid) {
      if (form.value.taskId) {
        await updateTask(form.value);
      } else {
        await addTask(form.value);
      }
      proxy?.$modal.msgSuccess('操作成功');
      dialog.visible = false;
      await getList();
    }
  });
};

const handleDelete = async (row?: EaTaskVO) => {
  const taskIds = row?.taskId || ids.value;
  await proxy?.$modal.confirm('是否确认删除任务编号为"' + taskIds + '"的数据项？');
  await delTask(taskIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

const handleRun = async (row?: EaTaskVO) => {
  const taskId = row?.taskId || ids.value[0];
  await proxy?.$modal.confirm('是否将任务编号为"' + taskId + '"重新入队，等待执行节点重新领取？');
  await runTask(taskId);
  proxy?.$modal.msgSuccess('任务已重新入队');
  await getList();
  if (detailVisible.value && detail.value.task?.taskId === taskId) {
    await handleDetail({ taskId } as EaTaskVO);
  }
};

onMounted(() => {
  getList();
});
</script>

<style scoped>
:deep(.task-detail-summary .el-descriptions__label.el-descriptions__cell) {
  width: 96px;
  min-width: 96px;
  white-space: nowrap;
}

.detail-json {
  margin: 0;
  padding: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}
</style>
