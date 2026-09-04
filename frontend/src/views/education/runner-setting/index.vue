<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="租户" prop="tenantId">
              <el-input v-model="queryParams.tenantId" placeholder="请输入租户" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="AI类型" prop="aiType">
              <el-input v-model="queryParams.aiType" placeholder="请输入AI类型" clearable @keyup.enter="handleQuery" />
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

      <el-table v-loading="loading" border :data="runnerSettingList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="配置ID" align="center" prop="settingId" width="100" />
        <el-table-column label="租户" align="center" prop="tenantId" width="140" />
        <el-table-column label="AI类型" align="center" prop="aiType" width="120" />
        <el-table-column label="AI模型" align="center" prop="aiModel" min-width="160" :show-overflow-tooltip="true" />
        <el-table-column label="AI地址" align="center" prop="aiUrl" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="外部题库" align="center" prop="externalQuestionUrl" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="轮询间隔" align="center" prop="pollIntervalSeconds" width="100" />
        <el-table-column label="并发上限" align="center" prop="maxParallelTasks" width="100" />
        <el-table-column label="超时秒数" align="center" prop="taskTimeoutSeconds" width="100" />
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

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="760px" append-to-body>
      <el-form ref="runnerSettingFormRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="租户" prop="tenantId">
          <el-input v-model="form.tenantId" placeholder="请输入租户" />
        </el-form-item>
        <el-form-item label="AI类型" prop="aiType">
          <el-input v-model="form.aiType" placeholder="如 openai / oneapi" />
        </el-form-item>
        <el-form-item label="AI地址" prop="aiUrl">
          <el-input v-model="form.aiUrl" placeholder="请输入 AI 地址" />
        </el-form-item>
        <el-form-item label="AI模型" prop="aiModel">
          <el-input v-model="form.aiModel" placeholder="请输入 AI 模型" />
        </el-form-item>
        <el-form-item label="AI密钥" prop="aiApiKey">
          <el-input v-model="form.aiApiKey" placeholder="请输入 AI 密钥" show-password />
        </el-form-item>
        <el-form-item label="外挂题库地址" prop="externalQuestionUrl">
          <el-input v-model="form.externalQuestionUrl" placeholder="请输入外挂题库地址" />
        </el-form-item>
        <el-form-item label="回复语气" prop="completionTone">
          <el-input-number v-model="form.completionTone" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="彩色日志" prop="colorLog">
          <el-select v-model="form.colorLog" style="width: 100%">
            <el-option label="关闭" :value="0" />
            <el-option label="开启" :value="1" />
          </el-select>
        </el-form-item>
        <el-form-item label="日志级别" prop="logLevel">
          <el-input v-model="form.logLevel" placeholder="如 info / debug" />
        </el-form-item>
        <el-form-item label="日志模式" prop="logModel">
          <el-input-number v-model="form.logModel" :min="0" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="轮询间隔(秒)" prop="pollIntervalSeconds">
          <el-input-number v-model="form.pollIntervalSeconds" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="最大并发" prop="maxParallelTasks">
          <el-input-number v-model="form.maxParallelTasks" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="任务超时(秒)" prop="taskTimeoutSeconds">
          <el-input-number v-model="form.taskTimeoutSeconds" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="日志保留(天)" prop="logRetentionDays">
          <el-input-number v-model="form.logRetentionDays" :min="1" controls-position="right" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="form.remark" type="textarea" placeholder="请输入备注" />
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

<script setup name="EduRunnerSetting" lang="ts">
import { addRunnerSetting, delRunnerSetting, getRunnerSetting, listRunnerSetting, updateRunnerSetting } from '@/api/education/runnerSetting';
import { EaRunnerSettingForm, EaRunnerSettingQuery, EaRunnerSettingVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const runnerSettingList = ref<EaRunnerSettingVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const runnerSettingFormRef = ref<ElFormInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const initFormData: EaRunnerSettingForm = {
  settingId: undefined,
  tenantId: '',
  aiType: '',
  aiUrl: '',
  aiModel: '',
  aiApiKey: '',
  externalQuestionUrl: '',
  completionTone: 0,
  colorLog: 0,
  logLevel: 'info',
  logModel: 0,
  pollIntervalSeconds: 60,
  maxParallelTasks: 1,
  taskTimeoutSeconds: 3600,
  logRetentionDays: 7,
  remark: ''
};

const data = reactive<PageData<EaRunnerSettingForm, EaRunnerSettingQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    tenantId: '',
    aiType: ''
  },
  rules: {
    tenantId: [{ required: true, message: '租户不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const getList = async () => {
  loading.value = true;
  const res = await listRunnerSetting(queryParams.value);
  runnerSettingList.value = res.rows;
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

const handleSelectionChange = (selection: EaRunnerSettingVO[]) => {
  ids.value = selection.map((item) => item.settingId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const reset = () => {
  form.value = { ...initFormData };
  runnerSettingFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = () => {
  reset();
  dialog.visible = true;
  dialog.title = '新增运行配置';
};

const handleUpdate = async (row?: EaRunnerSettingVO) => {
  reset();
  const settingId = row?.settingId || ids.value[0];
  const { data } = await getRunnerSetting(settingId);
  Object.assign(form.value, data);
  dialog.visible = true;
  dialog.title = '修改运行配置';
};

const submitForm = () => {
  runnerSettingFormRef.value?.validate(async (valid: boolean) => {
    if (valid) {
      if (form.value.settingId) {
        await updateRunnerSetting(form.value);
      } else {
        await addRunnerSetting(form.value);
      }
      proxy?.$modal.msgSuccess('操作成功');
      dialog.visible = false;
      await getList();
    }
  });
};

const handleDelete = async (row?: EaRunnerSettingVO) => {
  const settingIds = row?.settingId || ids.value;
  await proxy?.$modal.confirm('是否确认删除运行配置编号为"' + settingIds + '"的数据项？');
  await delRunnerSetting(settingIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

onMounted(() => {
  getList();
});
</script>
