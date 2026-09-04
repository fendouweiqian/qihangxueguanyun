<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="平台" prop="platformId">
              <el-select v-model="queryParams.platformId" placeholder="请选择平台" clearable style="width: 200px">
                <el-option v-for="item in platformOptions" :key="item.platformId" :label="item.platformName" :value="item.platformId"></el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="学校名称" prop="schoolName">
              <el-input v-model="queryParams.schoolName" placeholder="请输入学校名称" clearable @keyup.enter="handleQuery" />
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

        <el-table v-loading="loading" border :data="schoolList" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column label="学校ID" align="center" prop="schoolId" width="110" />
        <el-table-column label="平台" align="center" prop="platformId" width="100" />
        <el-table-column label="学校名称" align="center" prop="schoolName" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="访问类型" align="center" prop="accessType" width="100">
          <template #default="scope">
            <el-tag v-if="scope.row.accessType === 2" type="success">小程序</el-tag>
            <el-tag v-else type="info">网页</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="访问地址" align="center" prop="accessAddress" min-width="180" :show-overflow-tooltip="true" />
        <el-table-column label="学校地址" align="center" prop="schoolUrl" min-width="200" :show-overflow-tooltip="true" />
        <el-table-column label="状态" align="center" prop="schoolState" width="90" />
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

    <el-dialog v-model="dialog.visible" :title="dialog.title" width="820px" append-to-body>
      <el-form ref="schoolFormRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="平台" prop="platformId">
              <el-select v-model="form.platformId" placeholder="请选择平台" style="width: 100%">
                <el-option v-for="item in platformOptions" :key="item.platformId" :label="item.platformName" :value="item.platformId"></el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="学校名称" prop="schoolName">
              <el-input v-model="form.schoolName" placeholder="请输入学校名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="访问类型" prop="accessType">
              <el-select v-model="form.accessType" placeholder="请选择访问类型" style="width: 100%">
                <el-option label="网页" :value="1" />
                <el-option label="小程序" :value="2" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="访问地址" prop="accessAddress">
              <el-input v-model="form.accessAddress" placeholder="请输入访问地址/入口说明" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="学校地址" prop="schoolUrl">
              <el-input v-model="form.schoolUrl" placeholder="请输入学校地址" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="学校状态" prop="schoolState">
              <el-input-number v-model="form.schoolState" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="视频" prop="schoolVideo">
              <el-input-number v-model="form.schoolVideo" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="作业" prop="schoolWork">
              <el-input-number v-model="form.schoolWork" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试" prop="schoolExam">
              <el-input-number v-model="form.schoolExam" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="人脸" prop="schoolFace">
              <el-input-number v-model="form.schoolFace" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试2" prop="schoolExam2">
              <el-input-number v-model="form.schoolExam2" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试类型" prop="schoolExamType">
              <el-input-number v-model="form.schoolExamType" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="答题确认" prop="schoolAnswerOk">
              <el-input-number v-model="form.schoolAnswerOk" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="考试状态" prop="schoolExamState">
              <el-input-number v-model="form.schoolExamState" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="提交时间" prop="schoolSumbitTime">
              <el-input-number v-model="form.schoolSumbitTime" :min="0" controls-position="right" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="IP数量" prop="schoolIpNumber">
              <el-input-number v-model="form.schoolIpNumber" :min="0" controls-position="right" style="width: 100%" />
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

<script setup name="EduSchool" lang="ts">
import { addSchool, delSchool, getSchool, listSchool, updateSchool } from '@/api/education/school';
import { listPlatform } from '@/api/education/platform';
import { EaPlatformVO, EaSchoolForm, EaSchoolQuery, EaSchoolVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const schoolList = ref<EaSchoolVO[]>([]);
const platformOptions = ref<EaPlatformVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref<Array<number | string>>([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();
const schoolFormRef = ref<ElFormInstance>();

const dialog = reactive<DialogOption>({
  visible: false,
  title: ''
});

const initFormData: EaSchoolForm = {
  schoolId: undefined,
  platformId: undefined,
  schoolName: '',
  accessType: 1,
  accessAddress: '',
  schoolUrl: '',
  schoolState: 0,
  schoolVideo: 0,
  schoolWork: 0,
  schoolExam: 0,
  schoolFace: 0,
  schoolExam2: 0,
  schoolExamType: 0,
  schoolAnswerOk: 0,
  schoolExamState: 0,
  schoolSumbitTime: 0,
  schoolIpNumber: 0,
  schoolFid: '',
  schoolCode: '',
  schoolRemark: ''
};

const data = reactive<PageData<EaSchoolForm, EaSchoolQuery>>({
  form: { ...initFormData },
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    schoolName: '',
    platformId: undefined
  },
  rules: {
    platformId: [{ required: true, message: '平台不能为空', trigger: 'change' }],
    schoolName: [{ required: true, message: '学校名称不能为空', trigger: 'blur' }],
    accessType: [{ required: true, message: '访问类型不能为空', trigger: 'change' }],
    accessAddress: [{ required: true, message: '访问地址不能为空', trigger: 'blur' }]
  }
});

const { queryParams, form, rules } = toRefs(data);

const getPlatformOptions = async () => {
  const res = await listPlatform({ pageNum: 1, pageSize: 9999 });
  platformOptions.value = res.rows || [];
};

const getList = async () => {
  loading.value = true;
  const res = await listSchool(queryParams.value);
  schoolList.value = res.rows;
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

const handleSelectionChange = (selection: EaSchoolVO[]) => {
  ids.value = selection.map((item) => item.schoolId);
  single.value = selection.length !== 1;
  multiple.value = !selection.length;
};

const reset = () => {
  form.value = { ...initFormData };
  schoolFormRef.value?.resetFields();
};

const cancel = () => {
  reset();
  dialog.visible = false;
};

const handleAdd = async () => {
  reset();
  await getPlatformOptions();
  dialog.visible = true;
  dialog.title = '新增学校';
};

const handleUpdate = async (row?: EaSchoolVO) => {
  reset();
  await getPlatformOptions();
  const schoolId = row?.schoolId || ids.value[0];
  const { data } = await getSchool(schoolId);
  Object.assign(form.value, data);
  dialog.visible = true;
  dialog.title = '修改学校';
};

const submitForm = () => {
  schoolFormRef.value?.validate(async (valid: boolean) => {
    if (valid) {
      if (form.value.schoolId) {
        await updateSchool(form.value);
      } else {
        await addSchool(form.value);
      }
      proxy?.$modal.msgSuccess('操作成功');
      dialog.visible = false;
      await getList();
    }
  });
};

const handleDelete = async (row?: EaSchoolVO) => {
  const schoolIds = row?.schoolId || ids.value;
  await proxy?.$modal.confirm('是否确认删除学校编号为"' + schoolIds + '"的数据项？');
  await delSchool(schoolIds);
  await getList();
  proxy?.$modal.msgSuccess('删除成功');
};

onMounted(async () => {
  await getPlatformOptions();
  getList();
});
</script>
