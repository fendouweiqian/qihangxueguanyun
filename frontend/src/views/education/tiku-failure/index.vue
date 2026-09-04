<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="任务" prop="taskId">
              <el-input v-model="queryParams.taskId" placeholder="请输入任务ID" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="订单" prop="orderId">
              <el-input v-model="queryParams.orderId" placeholder="请输入订单ID" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="题库来源" prop="provider">
              <el-input v-model="queryParams.provider" placeholder="请输入题库来源" clearable @keyup.enter="handleQuery" />
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
          <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
        </el-row>
      </template>

      <el-table v-loading="loading" border :data="failureList">
        <el-table-column label="失败ID" align="center" prop="failureId" width="100" />
        <el-table-column label="任务ID" align="center" prop="taskId" width="100" />
        <el-table-column label="订单ID" align="center" prop="orderId" width="100" />
        <el-table-column label="题库来源" align="center" prop="provider" width="140" />
        <el-table-column label="题目" prop="question" min-width="260" :show-overflow-tooltip="true" />
        <el-table-column label="选项JSON" prop="optionsJson" min-width="220" :show-overflow-tooltip="true" />
        <el-table-column label="失败原因" prop="reason" min-width="220" :show-overflow-tooltip="true" />
        <el-table-column label="原始响应" prop="rawResponse" min-width="260" :show-overflow-tooltip="true" />
        <el-table-column label="时间" align="center" prop="createTime" width="180" />
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>
  </div>
</template>

<script setup name="EduTikuFailure" lang="ts">
import { listTikuFailure } from '@/api/education/tikuFailure';
import { EaTikuFailureQuery, EaTikuFailureVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const failureList = ref<EaTikuFailureVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();

const data = reactive<PageData<Record<string, never>, EaTikuFailureQuery>>({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    taskId: undefined,
    orderId: undefined,
    provider: ''
  },
  rules: {}
});

const { queryParams } = toRefs(data);

const getList = async () => {
  loading.value = true;
  const res = await listTikuFailure(queryParams.value);
  failureList.value = res.rows;
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

onMounted(() => {
  getList();
});
</script>
