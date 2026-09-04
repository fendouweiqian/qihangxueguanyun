<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="节点编码" prop="workerCode">
              <el-input v-model="queryParams.workerCode" placeholder="请输入节点编码" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="主机名" prop="hostName">
              <el-input v-model="queryParams.hostName" placeholder="请输入主机名" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="状态" prop="status">
              <el-select v-model="queryParams.status" placeholder="状态" clearable style="width: 140px">
                <el-option label="离线" :value="0" />
                <el-option label="在线" :value="1" />
                <el-option label="异常" :value="2" />
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
            <el-button type="danger" plain icon="Delete" :disabled="multiple" @click="handleDelete()">删除</el-button>
          </el-col>
          <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="runnerNodeList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="节点ID" align="center" prop="nodeId" width="100" />
        <el-table-column label="节点编码" align="center" prop="workerCode" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="主机名" align="center" prop="hostName" min-width="160" :show-overflow-tooltip="true" />
        <el-table-column label="版本" align="center" prop="version" width="140" />
        <el-table-column label="状态" align="center" width="100">
          <template #default="scope">
            <el-tag :type="statusTag(scope.row.status)">{{ statusLabel(scope.row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="当前任务" align="center" prop="currentTaskId" width="110" />
        <el-table-column label="当前订单" align="center" prop="currentOrderId" width="110" />
        <el-table-column label="最后心跳" align="center" prop="heartbeatAt" width="180" />
        <el-table-column label="最后错误" align="center" prop="lastError" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="120">
          <template #default="scope">
            <el-tooltip content="修改" placement="top">
              <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="danger" icon="Delete" @click="handleDelete(scope.row)"></el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="640px" append-to-body>
      <el-form ref="runnerNodeFormRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="节点编码" prop="workerCode">
          <el-input v-model="form.workerCode" placeholder="请输入节点编码" />
        </el-form-item>
        <el-form-item label="主机名" prop="hostName">
          <el-input v-model="form.hostName" placeholder="请输入主机名" />
        </el-form-item>
        <el-form-item label="版本" prop="version">
          <el-input v-model="form.version" placeholder="请输入版本" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" placeholder="请选择状态" style="width: 100%">
            <el-option label="离线" :value="0" />
            <el-option label="在线" :value="1" />
            <el-option label="异常" :value="2" />
          </el-select>
        </el-form-item>
        <el-form-item label="当前任务" prop="currentTaskId">
          <el-input v-model="form.currentTaskId" placeholder="请输入当前任务ID" />
        </el-form-item>
        <el-form-item label="当前订单" prop="currentOrderId">
          <el-input v-model="form.currentOrderId" placeholder="请输入当前订单ID" />
        </el-form-item>
        <el-form-item label="最后心跳" prop="heartbeatAt">
          <el-date-picker v-model="form.heartbeatAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="启动时间" prop="startedAt">
          <el-date-picker v-model="form.startedAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最后错误" prop="lastError">
          <el-input v-model="form.lastError" type="textarea" placeholder="请输入最后错误" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="primary" @click="submitForm">确 定</el-button>
          <el-button @click="cancel">取 消</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EduRunnerNode" lang="ts">
import { addRunnerNode, delRunnerNode, getRunnerNode, listRunnerNode, updateRunnerNode } from '@/api/education/runnerNode';
import { EaRunnerNodeForm, EaRunnerNodeQuery, EaRunnerNodeVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const runnerNodeList = ref<EaRunnerNodeVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const runnerNodeFormRef = ref<ElFormInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const initFormData: EaRunnerNodeForm = {
  nodeId: undefined,
  workerCode: '',
  version: '',
  hostName: '',
  status: 1,
  currentTaskId: undefined,
  currentOrderId: undefined,
  lastError: '',
  heartbeatAt: '',
  startedAt: ''
};

const data = reactive<PageData<EaRunnerNodeForm, EaRunnerNodeQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    workerCode: '',
    hostName: '',
    status: undefined
  },
  rules: {
    workerCode: [{ required: true, message: '节点编码不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const statusLabel = (status?: number) => {
  if (status === 1) {
    return '在线';
  }
  if (status === 2) {
    return '异常';
  }
  return '离线';
};

const statusTag = (status?: number) => {
  if (status === 1) {
    return 'success';
  }
  if (status === 2) {
    return 'danger';
  }
  return 'info';
};

const getList = async () => {
  loading.value = true;
  const res = await listRunnerNode(queryParams.value);
  runnerNodeList.value = res.rows;
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

const handleSelectionChange = (selection: EaRunnerNodeVO[]) => {
  ids.value = selection.map((item) => item.nodeId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const reset = () => {
  form.value = { ...initFormData };
  runnerNodeFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = () => {
  reset();
  dialog.visible = true;
  dialog.title = '新增运行节点';
};

const handleUpdate = async (row?: EaRunnerNodeVO) => {
  reset();
  const nodeId = row?.nodeId || ids.value[0];
  const { data } = await getRunnerNode(nodeId);
  Object.assign(form.value, data);
  dialog.visible = true;
  dialog.title = '修改运行节点';
};

const submitForm = () => {
  runnerNodeFormRef.value?.validate(async (valid: boolean) => {
    if (valid) {
      if (form.value.nodeId) {
        await updateRunnerNode(form.value);
      } else {
        await addRunnerNode(form.value);
      }
      proxy?.$modal.msgSuccess('操作成功');
      dialog.visible = false;
      await getList();
    }
  });
};

const handleDelete = async (row?: EaRunnerNodeVO) => {
  const nodeIds = row?.nodeId || ids.value;
  await proxy?.$modal.confirm('是否确认删除运行节点编号为"' + nodeIds + '"的数据项？');
  await delRunnerNode(nodeIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

onMounted(() => {
  getList();
});
</script>
