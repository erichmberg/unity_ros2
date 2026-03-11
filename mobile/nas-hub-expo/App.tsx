import React, { useMemo, useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ScrollView, View, Text, TextInput, Button, StyleSheet, RefreshControl, Alert } from 'react-native';

const Tab = createBottomTabNavigator();
const queryClient = new QueryClient();
const API_BASE = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://192.168.50.165:3180';

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${API_BASE}${path}`, init);
  if (!r.ok) throw new Error(`${path} failed (${r.status})`);
  return r.json();
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <View style={styles.card}>
      <Text style={styles.cardTitle}>{title}</Text>
      {children}
    </View>
  );
}

function DashboardScreen() {
  const [refreshing, setRefreshing] = useState(false);
  const eventsQ = useQuery({
    queryKey: ['events-today'],
    queryFn: async () => {
      const s = new Date(); s.setHours(0,0,0,0);
      const e = new Date(); e.setHours(23,59,59,999);
      return api<{items:any[]}>(`/api/events?start=${encodeURIComponent(s.toISOString())}&end=${encodeURIComponent(e.toISOString())}`);
    }
  });
  const thesisQ = useQuery({ queryKey: ['thesis-summary'], queryFn: () => api<any>('/api/thesis-summary?days=7') });
  const insightQ = useQuery({ queryKey: ['thesis-insights'], queryFn: () => api<any>('/api/thesis-insights?target_weekly_hours=20') });
  const deadlinesQ = useQuery({ queryKey: ['deadlines-active'], queryFn: () => api<any>('/api/deadlines?status=active') });

  const onRefresh = async () => {
    setRefreshing(true);
    await Promise.all([eventsQ.refetch(), thesisQ.refetch(), insightQ.refetch(), deadlinesQ.refetch()]);
    setRefreshing(false);
  };

  const events = eventsQ.data?.items || [];
  const deadlines = deadlinesQ.data?.items || [];

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}>
        <Card title="Today focus">
          {events.length ? events.slice(0, 6).map((ev: any) => (
            <Text key={ev.id} style={styles.rowText}>• {ev.summary || '(no title)'}</Text>
          )) : <Text style={styles.rowText}>No events today.</Text>}
        </Card>

        <Card title="Thesis progress">
          <Text style={styles.rowText}>Last 7 days: {thesisQ.data?.hours ?? '-'}h ({thesisQ.data?.entries ?? '-'} logs)</Text>
          <Text style={styles.rowText}>Total since start: {thesisQ.data?.totalProjectHours ?? '-'}h</Text>
          <Text style={styles.rowText}>{insightQ.data?.message ?? '...'}</Text>
        </Card>

        <Card title="Upcoming deadlines">
          {deadlines.length ? deadlines.slice(0, 6).map((d: any) => (
            <Text key={d.id} style={styles.rowText}>• {d.title} (done by {new Date(d.doneByAt).toLocaleDateString()})</Text>
          )) : <Text style={styles.rowText}>No active deadlines.</Text>}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function DeadlinesScreen() {
  const qc = useQueryClient();
  const [title, setTitle] = useState('');
  const [doneBy, setDoneBy] = useState('');
  const [deadlineAt, setDeadlineAt] = useState('');

  const listQ = useQuery({ queryKey: ['deadlines'], queryFn: () => api<any>('/api/deadlines') });
  const createM = useMutation({
    mutationFn: (payload: any) => api<any>('/api/deadlines', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['deadlines'] });
      qc.invalidateQueries({ queryKey: ['deadlines-active'] });
      setTitle(''); setDoneBy(''); setDeadlineAt('');
      Alert.alert('Created', 'Deadline created');
    },
    onError: (e: any) => Alert.alert('Error', e?.message || 'Create failed')
  });

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView>
        <Card title="Create deadline">
          <TextInput style={styles.input} placeholder="Assignment title" value={title} onChangeText={setTitle} />
          <TextInput style={styles.input} placeholder="Done-by (YYYY-MM-DDTHH:MM:SS)" value={doneBy} onChangeText={setDoneBy} />
          <TextInput style={styles.input} placeholder="Deadline (YYYY-MM-DDTHH:MM:SS)" value={deadlineAt} onChangeText={setDeadlineAt} />
          <Button title="Create" onPress={() => createM.mutate({
            title,
            doneByAt: doneBy,
            deadlineAt,
            remindStartDays: 14,
            remindEveryDays: 2,
            priority: 'normal',
            notes: '',
            calendarId: '193359d12d2d2315fd62fecc6d8f4f31facfb9c2515003750ca3a318d6f286f5@group.calendar.google.com',
            timeZone: 'Europe/Stockholm'
          })} />
        </Card>

        <Card title="Deadlines">
          {(listQ.data?.items || []).map((d: any) => (
            <Text key={d.id} style={styles.rowText}>• {d.title} — {new Date(d.deadlineAt).toLocaleString()}</Text>
          ))}
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function ThesisQuickLogScreen() {
  const [startedAt, setStartedAt] = useState('');
  const [hours, setHours] = useState('1');
  const [summary, setSummary] = useState('');

  const submit = async () => {
    try {
      const body = new URLSearchParams();
      body.set('started_at', startedAt);
      body.set('hours', hours);
      body.set('summary', summary);
      body.set('task_type', 'coding');
      const r = await fetch(`${API_BASE}/api/thesis-log`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString(),
      });
      if (!r.ok && r.status !== 303) throw new Error(`Failed (${r.status})`);
      Alert.alert('Saved', 'Thesis log saved');
      setSummary('');
    } catch (e: any) {
      Alert.alert('Error', e?.message || 'Save failed');
    }
  };

  return (
    <SafeAreaView style={styles.screen}>
      <ScrollView>
        <Card title="Quick thesis log">
          <TextInput style={styles.input} placeholder="Started at (YYYY-MM-DDTHH:MM)" value={startedAt} onChangeText={setStartedAt} />
          <TextInput style={styles.input} placeholder="Hours" value={hours} onChangeText={setHours} keyboardType="numeric" />
          <TextInput style={styles.input} placeholder="Summary" value={summary} onChangeText={setSummary} />
          <Button title="Save log" onPress={submit} />
        </Card>
      </ScrollView>
    </SafeAreaView>
  );
}

function Root() {
  return (
    <NavigationContainer>
      <Tab.Navigator>
        <Tab.Screen name="Dashboard" component={DashboardScreen} />
        <Tab.Screen name="Deadlines" component={DeadlinesScreen} />
        <Tab.Screen name="Thesis Log" component={ThesisQuickLogScreen} />
      </Tab.Navigator>
    </NavigationContainer>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Root />
    </QueryClientProvider>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: '#0e1116' },
  card: { backgroundColor: '#171b22', margin: 12, padding: 12, borderRadius: 12, borderWidth: 1, borderColor: '#2a313d' },
  cardTitle: { color: '#f2f5ff', fontSize: 16, fontWeight: '700', marginBottom: 8 },
  rowText: { color: '#d6dbea', marginBottom: 6 },
  input: { backgroundColor: '#0f1319', color: '#f2f5ff', borderWidth: 1, borderColor: '#2f3847', borderRadius: 8, padding: 10, marginBottom: 8 },
});
