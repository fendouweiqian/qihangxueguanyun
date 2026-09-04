<template>
  <div class="p-2">
    <transition :enter-active-class="proxy?.animate.searchAnimate.enter" :leave-active-class="proxy?.animate.searchAnimate.leave">
      <div v-show="showSearch" class="mb-[10px]">
        <el-card shadow="hover">
          <el-form ref="queryFormRef" :model="queryParams" :inline="true">
            <el-form-item label="租户" prop="tenantId">
              <el-input v-model="queryParams.tenantId" placeholder="请输入租户编号" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="订单ID" prop="orderId">
              <el-input v-model="queryParams.orderId" placeholder="请输入订单ID" clearable @keyup.enter="handleQuery" />
            </el-form-item>
            <el-form-item label="类型" prop="type">
              <el-input v-model="queryParams.type" placeholder="类型" clearable style="width: 120px" />
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
        <right-toolbar v-model:show-search="showSearch" @query-table="getList"></right-toolbar>
      </template>

      <el-table v-loading="loading" border :data="ledgerList">
        <el-table-column label="流水ID" align="center" prop="ledgerId" width="110" />
        <el-table-column label="租户" align="center" prop="tenantId" width="120" />
        <el-table-column label="订单ID" align="center" prop="orderId" min-width="170" />
        <el-table-column label="变动积分" align="center" prop="changePoints" width="100" />
        <el-table-column label="赠送积分" align="center" prop="giftPoints" width="100" />
        <el-table-column label="类型" align="center" prop="type" width="80" />
        <el-table-column label="操作人" align="center" prop="operatorUserId" width="100" />
        <el-table-column label="备注" align="center" prop="remark" min-width="160" :show-overflow-tooltip="true" />
        <el-table-column label="创建时间" align="center" prop="createTime" width="180" />
      </el-table>

      <pagination v-show="total > 0" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" :total="total" @pagination="getList" />
    </el-card>
  </div>
</template>

<script setup name="EduLedger" lang="ts">
import { listLedger } from '@/api/education/ledger';
import { EaLedgerQuery, EaLedgerVO } from '@/api/education/types';

const { proxy } = getCurrentInstance() as ComponentInternalInstance;

const ledgerList = ref<EaLedgerVO[]>([]);
const loading = ref(true);
const showSearch = ref(true);
const total = ref(0);

const queryFormRef = ref<ElFormInstance>();

const data = reactive<PageData<EaLedgerVO, EaLedgerQuery>>({
  form: {} as EaLedgerVO,
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    tenantId: '',
    orderId: undefined,
    type: undefined
  },
  rules: {}
});

const { queryParams } = toRefs(data);

const getList = async () => {
  loading.value = true;
  const res = await listLedger(queryParams.value);
  ledgerList.value = res.rows;
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
