<!-- Control Dashboard Page - Real Battery Control System -->
<template>
  <div class="space-y-6">
    <!-- Header with System Status -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-bolt" class="w-8 h-8 text-blue-500" />
            <h1 class="text-2xl font-bold text-gray-900 dark:text-white">
              🎮 Battery Control System
            </h1>
          </div>
          <div class="flex items-center space-x-3">
            <UBadge 
              :color="getStatusColor(systemStatus.mode)" 
              :label="systemStatus.mode?.toUpperCase() || 'UNKNOWN'"
              size="lg"
            />
            <UButton 
              @click="refreshStatus" 
              :loading="statusLoading"
              icon="i-heroicons-arrow-path"
              size="sm"
              variant="ghost"
            >
              Refresh
            </UButton>
          </div>
        </div>
      </template>
      
      <!-- Real-time System Status Grid -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <!-- Battery SOC -->
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-4xl font-bold mb-2" :class="getSocColor(systemStatus.soc)">
            {{ systemStatus.soc || 0 }}%
          </div>
          <UProgress 
            :value="systemStatus.soc || 0" 
            :max="100" 
            size="lg"
            :color="getSocProgressColor(systemStatus.soc)"
          />
          <p class="text-sm text-gray-500 mt-2">Battery State of Charge</p>
          <p class="text-xs text-gray-400">
            {{ ((systemStatus.soc || 0) * (systemStatus.battery_capacity_kwh || 10) / 100).toFixed(1) }}kWh available
          </p>
        </div>
        
        <!-- Current Power -->
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-4xl font-bold mb-2" :class="getPowerColor(systemStatus.power_kw)">
            {{ systemStatus.power_kw > 0 ? '+' : '' }}{{ systemStatus.power_kw || 0 }}kW
          </div>
          <UIcon 
            :name="getPowerIcon(systemStatus.power_kw)" 
            class="w-12 h-12 mx-auto mb-2"
            :class="getPowerIconColor(systemStatus.power_kw)"
          />
          <p class="text-sm text-gray-500">
            {{ getPowerStatus(systemStatus.power_kw) }}
          </p>
          <p class="text-xs text-gray-400" v-if="systemStatus.estimated_completion">
            Complete: {{ formatTime(systemStatus.estimated_completion) }}
          </p>
        </div>
        
        <!-- Active Command Status -->
        <div class="text-center p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div class="text-2xl font-semibold mb-2">
            {{ systemStatus.active_command?.toUpperCase() || 'IDLE' }}
          </div>
          <UBadge 
            v-if="systemStatus.active_command"
            :color="getCommandColor(systemStatus.active_command)"
            :label="systemStatus.active_command.toUpperCase()"
            size="lg"
          />
          <p class="text-sm text-gray-500 mt-2">Current Command</p>
          <p class="text-xs text-gray-400 mt-1" v-if="systemStatus.command_reason">
            {{ systemStatus.command_reason }}
          </p>
        </div>
      </div>
      
      <!-- Battery Health & Specifications -->
      <div class="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div class="text-lg font-semibold">{{ systemStatus.battery_capacity_kwh || 10 }}kWh</div>
          <p class="text-xs text-gray-500">Capacity</p>
        </div>
        <div>
          <div class="text-lg font-semibold">{{ systemStatus.max_power_kw || 5 }}kW</div>
          <p class="text-xs text-gray-500">Max Power</p>
        </div>
        <div>
          <div class="text-lg font-semibold text-green-600">
            {{ batteryHealth }}%
          </div>
          <p class="text-xs text-gray-500">Battery Health</p>
        </div>
        <div>
          <div class="text-lg font-semibold">
            {{ systemStatus.scheduled_commands_count || 0 }}
          </div>
          <p class="text-xs text-gray-500">Scheduled</p>
        </div>
      </div>
    </UCard>

    <!-- Manual Control Panel -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-cog-6-tooth" class="w-6 h-6 text-purple-500" />
            <h2 class="text-xl font-semibold">⚡ Manual Control</h2>
          </div>
          <UToggle 
            v-model="manualMode" 
            :label="manualMode ? 'Manual Mode ON' : 'Auto Mode ON'"
            :color="manualMode ? 'red' : 'green'"
          />
        </div>
      </template>
      
      <div v-if="manualMode" class="space-y-6">
        <!-- Power Setting Slider -->
        <UFormGroup label="Power Setting (kW)">
          <div class="space-y-4">
            <div class="flex items-center justify-center space-x-4">
              <span class="text-sm font-medium text-red-600 min-w-[80px]">
                Discharge {{ Math.abs(Math.min(0, manualPower)) }}kW
              </span>
              <div class="flex-1 px-4">
                <input
                  v-model="manualPower"
                  type="range"
                  :min="-maxPower" 
                  :max="maxPower"
                  :step="0.5"
                  class="w-full h-3 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
              </div>
              <span class="text-sm font-medium text-green-600 min-w-[80px]">
                Charge {{ Math.max(0, manualPower) }}kW
              </span>
            </div>
            
            <div class="text-center">
              <span class="text-2xl font-bold font-mono" :class="getPowerColor(manualPower)">
                {{ manualPower > 0 ? '+' : '' }}{{ manualPower }}kW
              </span>
            </div>
            
            <p class="text-xs text-gray-500 text-center">
              Negative = Discharge (sell to grid) | Positive = Charge (buy from grid)
            </p>
          </div>
        </UFormGroup>
        
        <!-- Quick Command Buttons -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <UButton 
            @click="executeCommand('charge', Math.abs(manualPower))"
            :disabled="!canCharge || manualPower <= 0"
            color="green"
            icon="i-heroicons-bolt"
            :loading="commandLoading"
            size="lg"
            block
          >
            Charge
            <br><span class="text-xs">{{ Math.abs(manualPower) }}kW</span>
          </UButton>
          
          <UButton 
            @click="executeCommand('discharge', Math.abs(manualPower))"
            :disabled="!canDischarge || manualPower >= 0"
            color="blue"
            icon="i-heroicons-lightning-bolt"
            :loading="commandLoading"
            size="lg"
            block
          >
            Discharge
            <br><span class="text-xs">{{ Math.abs(manualPower) }}kW</span>
          </UButton>
          
          <UButton 
            @click="executeCommand('hold', 0)"
            color="gray"
            icon="i-heroicons-pause"
            :loading="commandLoading"
            size="lg"
            block
          >
            Hold
            <br><span class="text-xs">Stop All</span>
          </UButton>
          
          <UButton 
            @click="executeCommand('auto', 0)"
            color="purple"
            icon="i-heroicons-cpu-chip"
            :loading="commandLoading"
            size="lg"
            block
          >
            Auto Mode
            <br><span class="text-xs">ML Control</span>
          </UButton>
        </div>
        
        <!-- Safety Warnings -->
        <UAlert 
          v-if="!canCharge && manualPower > 0"
          icon="i-heroicons-exclamation-triangle"
          color="amber"
          title="Charging Limited"
          description="Battery SOC too high or other safety limit active"
        />
        
        <UAlert 
          v-if="!canDischarge && manualPower < 0"
          icon="i-heroicons-exclamation-triangle"
          color="amber" 
          title="Discharge Limited"
          description="Battery SOC too low or other safety limit active"
        />
      </div>
      
      <div v-else class="text-center py-8">
        <UIcon name="i-heroicons-cpu-chip" class="w-16 h-16 mx-auto mb-4 text-purple-500" />
        <UAlert icon="i-heroicons-information-circle" title="Automatic Mode Active">
          System is operating under ML-driven automatic control. Enable manual mode to override.
        </UAlert>
        
        <div class="mt-4 grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
          <div>
            <UIcon name="i-heroicons-chart-bar" class="w-6 h-6 mx-auto mb-2" />
            <p>Smart price optimization</p>
          </div>
          <div>
            <UIcon name="i-heroicons-shield-check" class="w-6 h-6 mx-auto mb-2" />
            <p>Battery protection</p>
          </div>
          <div>
            <UIcon name="i-heroicons-clock" class="w-6 h-6 mx-auto mb-2" />
            <p>24/7 monitoring</p>
          </div>
        </div>
      </div>
    </UCard>

    <!-- Scheduled Commands -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-calendar-days" class="w-6 h-6 text-indigo-500" />
            <h2 class="text-xl font-semibold">📅 Scheduled Commands</h2>
          </div>
          <UButton 
            @click="showScheduleModal = true" 
            icon="i-heroicons-plus"
            color="indigo"
          >
            Add Schedule
          </UButton>
        </div>
      </template>
      
      <div v-if="scheduledCommands && scheduledCommands.length > 0" class="space-y-3">
        <div 
          v-for="schedule in scheduledCommands" 
          :key="schedule.id" 
          class="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
        >
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <div class="flex items-center space-x-2 mb-2">
                <UBadge 
                  :color="getCommandColor(schedule.command)" 
                  :label="schedule.command?.toUpperCase()" 
                />
                <span class="font-semibold">{{ schedule.power_kw }}kW</span>
              </div>
              
              <p class="text-sm text-gray-600 dark:text-gray-400 mb-1">
                <UIcon name="i-heroicons-clock" class="w-4 h-4 inline mr-1" />
                {{ formatScheduleTime(schedule.scheduled_time) }}
              </p>
              
              <p class="text-xs text-gray-500" v-if="schedule.reason">
                {{ schedule.reason }}
              </p>
            </div>
            
            <div class="flex items-center space-x-2">
              <UBadge 
                :color="schedule.status === 'pending' ? 'blue' : 'gray'" 
                :label="schedule.status || 'pending'"
                size="sm"
              />
              <UButton 
                @click="removeSchedule(schedule.id)" 
                size="xs" 
                color="red" 
                variant="ghost"
                icon="i-heroicons-trash"
              />
            </div>
          </div>
        </div>
      </div>
      
      <div v-else class="text-center py-8">
        <UIcon name="i-heroicons-calendar-days" class="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <p class="text-gray-500">No scheduled commands</p>
        <p class="text-xs text-gray-400 mt-1">
          Add scheduled commands to automate battery control
        </p>
      </div>
    </UCard>

    <!-- Command History -->
    <UCard>
      <template #header>
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <UIcon name="i-heroicons-clock" class="w-6 h-6 text-gray-500" />
            <h2 class="text-xl font-semibold">📜 Command History</h2>
          </div>
          <UButton 
            @click="refreshHistory" 
            icon="i-heroicons-arrow-path"
            size="sm"
            variant="ghost"
          >
            Refresh
          </UButton>
        </div>
      </template>
      
      <div v-if="commandHistory && commandHistory.length > 0" class="space-y-2 max-h-96 overflow-y-auto">
        <div 
          v-for="cmd in commandHistory.slice().reverse()" 
          :key="`${cmd.timestamp}-${cmd.command}`" 
          class="flex justify-between items-center border-b border-gray-100 dark:border-gray-800 pb-2 hover:bg-gray-50 dark:hover:bg-gray-800 px-2 py-1 rounded"
        >
          <div class="flex items-center space-x-3">
            <UBadge 
              :color="getCommandColor(cmd.command)" 
              :label="cmd.command?.toUpperCase()" 
              size="sm"
            />
            <span v-if="cmd.power_kw" class="text-sm font-medium text-gray-700 dark:text-gray-300">
              {{ cmd.power_kw }}kW
            </span>
            <span class="text-xs text-gray-500">
              SOC: {{ (cmd.soc_after * 100).toFixed(1) }}%
            </span>
          </div>
          
          <div class="text-right">
            <p class="text-sm font-medium">{{ formatTime(cmd.timestamp) }}</p>
            <p class="text-xs text-gray-500 max-w-xs truncate" :title="cmd.reason">
              {{ cmd.reason }}
            </p>
          </div>
        </div>
      </div>
      
      <div v-else class="text-center py-8">
        <UIcon name="i-heroicons-clock" class="w-16 h-16 mx-auto mb-4 text-gray-400" />
        <p class="text-gray-500">No command history available</p>
      </div>
    </UCard>

    <!-- Physics Simulator Status -->
    <UCard v-if="batteryPhysics">
      <template #header>
        <div class="flex items-center space-x-3">
          <UIcon name="i-heroicons-beaker" class="w-6 h-6 text-emerald-500" />
          <h2 class="text-xl font-semibold">🔬 Battery Physics Simulator</h2>
        </div>
      </template>
      
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
        <div>
          <div class="text-lg font-semibold text-emerald-600">
            {{ batteryPhysics.battery_type }}
          </div>
          <p class="text-xs text-gray-500">Battery Type</p>
        </div>
        <div>
          <div class="text-lg font-semibold">
            {{ (batteryPhysics.state?.soh * 100 || 100).toFixed(1) }}%
          </div>
          <p class="text-xs text-gray-500">State of Health</p>
        </div>
        <div>
          <div class="text-lg font-semibold">
            {{ (batteryPhysics.state?.cycles_completed || 0).toFixed(0) }}
          </div>
          <p class="text-xs text-gray-500">Cycles Completed</p>
        </div>
        <div>
          <div class="text-lg font-semibold">
            {{ (batteryPhysics.current_efficiency * 100 || 95).toFixed(1) }}%
          </div>
          <p class="text-xs text-gray-500">Current Efficiency</p>
        </div>
      </div>
      
      <div class="mt-4 text-xs text-gray-500 text-center">
        Physics model: {{ batteryPhysics.battery_type }} | 
        Max Charge: {{ batteryPhysics.max_charge_power?.toFixed(1) }}kW | 
        Max Discharge: {{ batteryPhysics.max_discharge_power?.toFixed(1) }}kW
      </div>
    </UCard>
  </div>

  <!-- Schedule Modal -->
  <UModal v-model="showScheduleModal" :ui="{ width: 'sm:max-w-md' }">
    <UCard>
      <template #header>
        <h3 class="text-lg font-semibold">Schedule Command</h3>
      </template>
      
      <UForm :state="newSchedule" @submit="addSchedule" class="space-y-4">
        <UFormGroup label="Command" name="command" required>
          <USelectMenu 
            v-model="newSchedule.command" 
            :options="commandOptions"
            option-attribute="label"
            value-attribute="value"
          />
        </UFormGroup>
        
        <UFormGroup label="Power (kW)" name="power" required>
          <UInput 
            v-model="newSchedule.power_kw" 
            type="number" 
            step="0.5" 
            :min="0"
            :max="maxPower"
            placeholder="Enter power in kW"
          />
        </UFormGroup>
        
        <UFormGroup label="Scheduled Time" name="time" required>
          <UInput 
            v-model="newSchedule.scheduled_time" 
            type="datetime-local" 
            :min="minScheduleTime"
          />
        </UFormGroup>
        
        <UFormGroup label="Reason" name="reason">
          <UInput 
            v-model="newSchedule.reason" 
            placeholder="Why schedule this command?"
          />
        </UFormGroup>
        
        <div class="flex justify-end space-x-3 pt-4">
          <UButton @click="showScheduleModal = false" variant="ghost" color="gray">
            Cancel
          </UButton>
          <UButton 
            type="submit" 
            :loading="scheduleLoading"
            icon="i-heroicons-calendar-days"
          >
            Schedule
          </UButton>
        </div>
      </UForm>
    </UCard>
  </UModal>
</template>

<script setup>
// Metadata
definePageMeta({
  title: 'Battery Control System',
  description: 'Real-time battery control and monitoring'
})

// Imports
import { ref, computed, onMounted, onUnmounted } from 'vue'

// Toast for notifications
const toast = useToast()

// Reactive state
const systemStatus = ref({
  soc: 50,
  power_kw: 0,
  mode: 'automatic',
  active_command: null,
  command_reason: null,
  battery_capacity_kwh: 10,
  max_power_kw: 5,
  last_update: new Date().toISOString(),
  estimated_completion: null,
  scheduled_commands_count: 0
})

const commandHistory = ref([])
const scheduledCommands = ref([])
const batteryPhysics = ref(null)

// UI state
const manualMode = ref(false)
const manualPower = ref(0)
const statusLoading = ref(false)
const commandLoading = ref(false)
const scheduleLoading = ref(false)
const showScheduleModal = ref(false)

// New schedule form
const newSchedule = ref({
  command: 'charge',
  power_kw: 2,
  scheduled_time: '',
  reason: ''
})

// Command options for dropdown
const commandOptions = [
  { label: 'Charge', value: 'charge' },
  { label: 'Discharge', value: 'discharge' },
  { label: 'Hold', value: 'hold' }
]

// Computed properties
const maxPower = computed(() => systemStatus.value.max_power_kw || 5)

const canCharge = computed(() => {
  return (systemStatus.value.soc || 0) < 95 && !commandLoading.value
})

const canDischarge = computed(() => {
  return (systemStatus.value.soc || 0) > 10 && !commandLoading.value
})

const batteryHealth = computed(() => {
  return batteryPhysics.value?.state?.soh 
    ? (batteryPhysics.value.state.soh * 100).toFixed(1)
    : '100.0'
})

const minScheduleTime = computed(() => {
  const now = new Date()
  now.setMinutes(now.getMinutes() + 5) // Minimum 5 minutes from now
  return now.toISOString().slice(0, 16)
})

// Status color functions
const getStatusColor = (mode) => {
  const colors = {
    'manual': 'red',
    'automatic': 'green', 
    'scheduled': 'blue'
  }
  return colors[mode] || 'gray'
}

const getSocColor = (soc) => {
  if (soc >= 80) return 'text-green-600'
  if (soc >= 60) return 'text-blue-600'  
  if (soc >= 40) return 'text-yellow-600'
  if (soc >= 20) return 'text-orange-600'
  return 'text-red-600'
}

const getSocProgressColor = (soc) => {
  if (soc >= 80) return 'green'
  if (soc >= 60) return 'blue'
  if (soc >= 40) return 'yellow'
  if (soc >= 20) return 'orange'
  return 'red'
}

const getPowerColor = (power) => {
  if (power > 0) return 'text-green-600'
  if (power < 0) return 'text-blue-600'
  return 'text-gray-600'
}

const getPowerIcon = (power) => {
  if (power > 0) return 'i-heroicons-arrow-down-circle'  // Charging (power in)
  if (power < 0) return 'i-heroicons-arrow-up-circle'    // Discharging (power out) 
  return 'i-heroicons-pause-circle'  // Idle
}

const getPowerIconColor = (power) => {
  if (power > 0) return 'text-green-500'
  if (power < 0) return 'text-blue-500'
  return 'text-gray-500'
}

const getPowerStatus = (power) => {
  if (power > 0) return 'Charging'
  if (power < 0) return 'Discharging' 
  return 'Idle'
}

const getCommandColor = (command) => {
  const colors = {
    'charge': 'green',
    'discharge': 'blue',
    'hold': 'gray',
    'auto': 'purple'
  }
  return colors[command] || 'gray'
}

// API functions
const refreshStatus = async () => {
  statusLoading.value = true
  try {
    const [statusData, physicsData] = await Promise.all([
      $fetch('/api/control/status'),
      $fetch('/api/control/physics').catch(() => null)
    ])
    
    if (statusData) {
      systemStatus.value = { ...systemStatus.value, ...statusData }
    }
    
    if (physicsData) {
      batteryPhysics.value = physicsData
    }
    
    console.log('Status refreshed:', statusData)
  } catch (error) {
    console.error('Failed to refresh status:', error)
    toast.add({
      title: 'Status Refresh Failed',
      description: error.message || 'Could not fetch system status',
      color: 'red'
    })
  } finally {
    statusLoading.value = false
  }
}

const refreshHistory = async () => {
  try {
    const [historyData, scheduledData] = await Promise.all([
      $fetch('/api/control/history'),
      $fetch('/api/control/scheduled').catch(() => [])
    ])
    
    commandHistory.value = historyData || []
    scheduledCommands.value = scheduledData || []
    
    console.log('History refreshed:', historyData?.length, 'commands')
  } catch (error) {
    console.error('Failed to refresh history:', error)
    toast.add({
      title: 'History Refresh Failed', 
      description: 'Could not fetch command history',
      color: 'amber'
    })
  }
}

const executeCommand = async (command, power) => {
  commandLoading.value = true
  
  try {
    const payload = {
      command,
      power_kw: command === 'discharge' ? -Math.abs(power) : Math.abs(power),
      reason: `Manual control: ${command} ${Math.abs(power)}kW`,
      user_id: 'dashboard_user'
    }
    
    console.log('Executing command:', payload)
    
    const result = await $fetch('/api/control/execute', {
      method: 'POST',
      body: payload
    })
    
    if (result.success) {
      // Update local status immediately for better UX
      systemStatus.value.active_command = command
      systemStatus.value.power_kw = payload.power_kw
      systemStatus.value.command_reason = payload.reason
      
      // Refresh full status
      await refreshStatus()
      await refreshHistory()
      
      toast.add({
        title: 'Command Executed',
        description: `${command.toUpperCase()} command sent successfully`,
        color: 'green',
        icon: 'i-heroicons-check-circle'
      })
    } else {
      throw new Error(result.message || 'Command execution failed')
    }
    
  } catch (error) {
    console.error('Command execution failed:', error)
    toast.add({
      title: 'Command Failed',
      description: error.message || `Failed to execute ${command} command`,
      color: 'red',
      icon: 'i-heroicons-exclamation-circle'
    })
  } finally {
    commandLoading.value = false
  }
}

const addSchedule = async () => {
  scheduleLoading.value = true
  
  try {
    const payload = {
      command: newSchedule.value.command,
      power_kw: newSchedule.value.power_kw,
      scheduled_time: newSchedule.value.scheduled_time,
      reason: newSchedule.value.reason || `Scheduled ${newSchedule.value.command}`
    }
    
    const result = await $fetch('/api/control/schedule', {
      method: 'POST',
      body: payload
    })
    
    if (result.success) {
      showScheduleModal.value = false
      
      // Reset form
      newSchedule.value = {
        command: 'charge',
        power_kw: 2,
        scheduled_time: '',
        reason: ''
      }
      
      await refreshHistory()
      
      toast.add({
        title: 'Command Scheduled',
        description: `${payload.command.toUpperCase()} scheduled successfully`,
        color: 'green'
      })
    } else {
      throw new Error(result.message || 'Schedule creation failed')
    }
    
  } catch (error) {
    console.error('Schedule creation failed:', error)
    toast.add({
      title: 'Schedule Failed',
      description: error.message || 'Failed to schedule command',
      color: 'red'
    })
  } finally {
    scheduleLoading.value = false
  }
}

const removeSchedule = async (scheduleId) => {
  try {
    const result = await $fetch(`/api/control/schedule/${scheduleId}`, {
      method: 'DELETE'
    })
    
    if (result.success) {
      await refreshHistory()
      
      toast.add({
        title: 'Schedule Removed',
        description: 'Scheduled command cancelled',
        color: 'blue'
      })
    }
    
  } catch (error) {
    console.error('Schedule removal failed:', error)
    toast.add({
      title: 'Removal Failed',
      description: 'Could not cancel scheduled command',
      color: 'red'
    })
  }
}

// Utility functions
const formatTime = (timestamp) => {
  if (!timestamp) return '--'
  try {
    return new Date(timestamp).toLocaleString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      day: '2-digit',
      month: '2-digit'
    })
  } catch {
    return '--'
  }
}

const formatScheduleTime = (timestamp) => {
  if (!timestamp) return '--'
  try {
    return new Date(timestamp).toLocaleString('en-US', {
      weekday: 'short',
      hour: '2-digit', 
      minute: '2-digit',
      day: '2-digit',
      month: '2-digit'
    })
  } catch {
    return '--'
  }
}

// Auto-refresh setup
let refreshInterval = null

onMounted(async () => {
  // Initial data load
  await Promise.all([
    refreshStatus(),
    refreshHistory()
  ])
  
  // Set up auto-refresh every 5 seconds for status, 30 seconds for history
  refreshInterval = setInterval(async () => {
    await refreshStatus()
    
    // Refresh history less frequently
    if (Math.random() < 0.2) { // 20% chance = roughly every 25 seconds
      await refreshHistory()
    }
  }, 5000)
  
  console.log('Control page mounted, auto-refresh enabled')
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  console.log('Control page unmounted, auto-refresh disabled')
})

// Watch manual mode toggle
watch(manualMode, async (isManual) => {
  if (!isManual) {
    // When switching to auto mode, execute auto command
    await executeCommand('auto', 0)
  }
})
</script>

<style scoped>
/* Custom styles for the range slider */
input[type="range"] {
  background: linear-gradient(to right, #ef4444 0%, #ef4444 50%, #10b981 50%, #10b981 100%);
}

input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  height: 20px;
  width: 20px;
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

input[type="range"]::-moz-range-thumb {
  height: 20px;
  width: 20px; 
  border-radius: 50%;
  background: #3b82f6;
  cursor: pointer;
  border: 2px solid white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

/* Animation for status changes */
.status-change {
  transition: all 0.3s ease-in-out;
}
</style>