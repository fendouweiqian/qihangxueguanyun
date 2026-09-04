<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="来源学校ID" prop="sourceSchoolId">
              <el-input v-model="queryParams.sourceSchoolId" placeholder="请输入来源学校ID" clearable style="width: 160px" />
            </el-form-item>
            <el-form-item label="平台" prop="platformId">
              <el-select v-model="queryParams.platformId" placeholder="请选择平台" clearable style="width: 200px">
                <el-option v-for="item in platformOptions" :key="item.platformId" :label="item.platformName" :value="item.platformId"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="平台名称" prop="platformName">
              <el-input v-model="queryParams.platformName" placeholder="平台名称" clearable style="width: 160px" />
            </el-form-item>
            <el-form-item label="学校名称" prop="schoolName">
              <el-input v-model="queryParams.schoolName" placeholder="请输入学校名称" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="启用状态" prop="enabled">
              <el-select v-model="queryParams.enabled" placeholder="请选择" clearable style="width: 120px">
                <el-option v-for="item in enabledOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
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

      <el-table v-loading="loading" border :data="schoolCacheList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="缓存ID" align="center" prop="cacheId" width="90" />
        <el-table-column label="来源学校ID" align="center" prop="sourceSchoolId" width="110" />
        <el-table-column label="平台" align="center" prop="platformName" width="140" />
        <el-table-column label="学校名称" align="center" prop="schoolName" min-width="200" :show-overflow-tooltip="true" />
        <el-table-column label="启用" align="center" prop="enabled" width="80">
          <template #default="scope">
            <el-tag :type="scope.row.enabled === 1 ? 'success' : 'info'">{{ scope.row.enabled === 1 ? '启用' : '停用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="网课" align="center" prop="videoSupported" width="90">
          <template #default="scope">
            <el-tag :type="supportTag(scope.row.videoSupported)">{{ supportLabel(scope.row.videoSupported) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="作业" align="center" prop="workSupported" width="90">
          <template #default="scope">
            <el-tag :type="supportTag(scope.row.workSupported)">{{ supportLabel(scope.row.workSupported) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="考试" align="center" prop="examSupported" width="90">
          <template #default="scope">
            <el-tag :type="supportTag(scope.row.examSupported)">{{ supportLabel(scope.row.examSupported) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="考试特殊下单" align="center" prop="examSpecialOrderRequired" width="130">
          <template #default="scope">
            <el-tag :type="requireTag(scope.row.examSpecialOrderRequired)">{{ requireLabel(scope.row.examSpecialOrderRequired) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="人脸识别" align="center" prop="faceRequired" width="90">
          <template #default="scope">
            <el-tag :type="requireTag(scope.row.faceRequired)">{{ requireLabel(scope.row.faceRequired) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交时间" align="center" prop="submitTime" width="90" />
        <el-table-column label="IP数量" align="center" prop="ipNumber" width="90" />
        <el-table-column label="创建时间" align="center" prop="createTime" width="180" />
        <el-table-column label="操作" align="center" class-name="small-padding fixed-width" width="120">
          <template #default="scope">
            <el-tooltip content="修改" placement="top">
              <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)"></el-button>
            </el-tooltip>
            <el-tooltip content="删除" placement="top">
              <el-button link type="primary" icon="Delete" @click="handleDelete(scope.row)"></el-button>
            </el-tooltip>
          </template>
        </el-table-column>
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="980px" append-to-body>
      <el-form ref="schoolCacheFormRef" :model="form" :rules="rules" label-width="120px">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="来源学校ID" prop="sourceSchoolId">
              <el-input v-model="form.sourceSchoolId" placeholder="请输入来源学校ID" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="平台" prop="platformId">
              <el-select v-model="form.platformId" placeholder="请选择平台" style="width: 100%" @change="handlePlatformChange">
                <el-option v-for="item in platformOptions" :key="item.platformId" :label="item.platformName" :value="item.platformId"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="平台名称" prop="platformName">
              <el-input v-model="form.platformName" placeholder="请输入平台名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学校名称" prop="schoolName">
              <el-input v-model="form.schoolName" placeholder="请输入学校名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学校地址" prop="schoolUrl">
              <el-input v-model="form.schoolUrl" placeholder="请输入学校地址" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="启用状态" prop="enabled">
              <el-switch v-model="form.enabled" :active-value="1" :inactive-value="0" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="网课" prop="videoSupported">
              <el-select v-model="form.videoSupported" placeholder="请选择" style="width: 100%">
                <el-option v-for="item in supportOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="作业" prop="workSupported">
              <el-select v-model="form.workSupported" placeholder="请选择" style="width: 100%">
                <el-option v-for="item in supportOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试" prop="examSupported">
              <el-select v-model="form.examSupported" placeholder="请选择" style="width: 100%">
                <el-option v-for="item in supportOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试特殊下单" prop="examSpecialOrderRequired">
              <el-select v-model="form.examSpecialOrderRequired" placeholder="请选择" style="width: 100%">
                <el-option v-for="item in requireOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="人脸识别" prop="faceRequired">
              <el-select v-model="form.faceRequired" placeholder="请选择" style="width: 100%">
                <el-option v-for="item in requireOptions" :key="item.value" :label="item.label" :value="item.value"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试类型" prop="examType">
              <el-input-number v-model="form.examType" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="答题确认" prop="answerOk">
              <el-input-number v-model="form.answerOk" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试状态" prop="examState">
              <el-input-number v-model="form.examState" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="提交时间" prop="submitTime">
              <el-input-number v-model="form.submitTime" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="IP数量" prop="ipNumber">
              <el-input-number v-model="form.ipNumber" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="FID" prop="schoolFid">
              <el-input v-model="form.schoolFid" placeholder="请输入FID" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学校编码" prop="schoolCode">
              <el-input v-model="form.schoolCode" placeholder="请输入学校编码" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="学校备注" prop="schoolRemark">
              <el-input v-model="form.schoolRemark" placeholder="请输入学校备注" type="textarea" />
            </el-form-item>
          </el-col>
        </el-row>
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

<script setup name="EduSchoolCache" lang="ts">
import { addSchoolCache, delSchoolCache, getSchoolCache, listSchoolCache, updateSchoolCache } from '@/api/education/schoolCache';
import { listPlatform } from '@/api/education/platform';
import { EaPlatformVO, EaSchoolCacheForm, EaSchoolCacheQuery, EaSchoolCacheVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const schoolCacheList = ref<EaSchoolCacheVO[]>([]);
const platformOptions = ref<EaPlatformVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const schoolCacheFormRef = ref<ElFormInstance>();

const enabledOptions = [
  { label: '启用', value: 1 },
  { label: '停用', value: 0 }
];

const supportOptions = [
  { label: '未知', value: 0, tagType: 'info' },
  { label: '支持', value: 1, tagType: 'success' },
  { label: '不支持', value: 2, tagType: 'danger' }
];

const requireOptions = [
  { label: '未知', value: 0, tagType: 'info' },
  { label: '需要', value: 1, tagType: 'warning' },
  { label: '不需要', value: 2, tagType: 'success' }
];

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const initFormData: EaSchoolCacheForm = {
  cacheId: undefined,
  sourceSchoolId: undefined,
  platformId: undefined,
  platformName: '',
  schoolName: '',
  schoolUrl: '',
  schoolFid: '',
  schoolCode: '',
  schoolRemark: '',
  enabled: 1,
  videoSupported: 0,
  workSupported: 0,
  examSupported: 0,
  examSpecialOrderRequired: 0,
  faceRequired: 0,
  examType: 0,
  answerOk: 0,
  examState: 0,
  submitTime: 0,
  ipNumber: 0
};

const data = reactive<PageData<EaSchoolCacheForm, EaSchoolCacheQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    sourceSchoolId: undefined,
    platformId: undefined,
    platformName: '',
    schoolName: '',
    enabled: undefined
  },
  rules: {
    sourceSchoolId: [{ required: true, message: '来源学校ID不能为空', trigger: 'blur' }],
    platformId: [{ required: true, message: '平台不能为空', trigger: 'change' }],
    platformName: [{ required: true, message: '平台名称不能为空', trigger: 'blur' }],
    schoolName: [{ required: true, message: '学校名称不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const getPlatformOptions = async () => {
  const res = await listPlatform({ pageNum: 1, pageSize: 9999 });
  platformOptions.value = res.rows || [];
};

const supportLabel = (value?: number) => {
  const matched = supportOptions.find((item) => item.value === value);
  return matched ? matched.label : '未知';
};

const supportTag = (value?: number): ElTagType => {
  const matched = supportOptions.find((item) => item.value === value);
  return (matched ? matched.tagType : 'info') as ElTagType;
};

const requireLabel = (value?: number) => {
  const matched = requireOptions.find((item) => item.value === value);
  return matched ? matched.label : '未知';
};

const requireTag = (value?: number): ElTagType => {
  const matched = requireOptions.find((item) => item.value === value);
  return (matched ? matched.tagType : 'info') as ElTagType;
};

const handlePlatformChange = (value: number | string) => {
  const match = platformOptions.value.find((item) => item.platformId === value);
  if (match) {
    form.value.platformName = match.platformName;
  }
};

const getList = async () => {
  loading.value = true;
  const res = await listSchoolCache(queryParams.value);
  schoolCacheList.value = res.rows;
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

const handleSelectionChange = (selection: EaSchoolCacheVO[]) => {
  ids.value = selection.map((item) => item.cacheId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const handleAdd = () => {
  resetForm();
  dialog.title = '新增学校缓存';
  dialog.visible = true;
};

const handleUpdate = async (row?: EaSchoolCacheVO) => {
  resetForm();
  const cacheId = row?.cacheId || ids.value[0];
  const res = await getSchoolCache(cacheId);
  Object.assign(form.value, res.data);
  dialog.title = '修改学校缓存';
  dialog.visible = true;
};

const submitForm = () => {
  schoolCacheFormRef.value?.validate(async (valid: boolean) => {
    if (!valid) return;
    if (form.value.cacheId) {
      await updateSchoolCache(form.value);
    } else {
      await addSchoolCache(form.value);
    }
    proxy?.$modal.msgSuccess('操作成功');
    dialog.visible = false;
    await getList();
  });
};

const handleDelete = async (row?: EaSchoolCacheVO) => {
  const cacheIds = row?.cacheId || ids.value;
  await proxy?.$modal.confirm('是否确认删除缓存ID为"' + cacheIds + '"的数据项？');
  await delSchoolCache(cacheIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

const cancel = () => {
  resetForm();
  dialog.visible = false;
};

const resetForm = () => {
  form.value = { ...initFormData };
  schoolCacheFormRef.value?.resetFields();
};

onMounted(async () => {
  await getPlatformOptions();
  await getList();
});
</script>
