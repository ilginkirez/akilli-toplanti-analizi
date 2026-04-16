import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Avatar, AvatarFallback, AvatarImage } from '../components/ui/avatar';
import { Input } from '../components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { CheckCircle2, Clock, AlertCircle, Plus, Search, Sparkles, GripVertical } from 'lucide-react';
import { mockTasks } from '../data/mockData';
import { getRelativeTime, getTaskStatusColor, getTaskStatusLabel, getPriorityColor, getPriorityLabel, getInitials } from '../utils/helpers';
import { useState } from 'react';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import type { Task } from '../types';

const ITEM_TYPE = 'TASK';

interface DraggableTaskProps {
  task: Task;
  onStatusChange: (taskId: string, newStatus: Task['status']) => void;
}

function DraggableTask({ task, onStatusChange }: DraggableTaskProps) {
  const [{ isDragging }, drag] = useDrag(() => ({
    type: ITEM_TYPE,
    item: { id: task.id, status: task.status },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  }));

  return (
    <div
      ref={drag}
      className={`group cursor-move ${isDragging ? 'opacity-50' : ''}`}
    >
      <Card className="border-gray-200 dark:border-gray-800 hover:shadow-md transition-shadow">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <GripVertical className="h-4 w-4 text-gray-400 mt-1 opacity-0 group-hover:opacity-100 transition-opacity" />
            <div className="flex-1 min-w-0">
              <div className="flex items-start justify-between gap-2 mb-2">
                <h4 className="font-semibold text-sm line-clamp-2">{task.title}</h4>
                <Badge className={getPriorityColor(task.priority)} variant="outline">
                  {getPriorityLabel(task.priority)}
                </Badge>
              </div>
              {task.description && (
                <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2 mb-3">
                  {task.description}
                </p>
              )}
              <div className="flex items-center justify-between">
                <Avatar className="h-7 w-7">
                  <AvatarImage src={task.assignee.avatar} />
                  <AvatarFallback className="text-xs">{getInitials(task.assignee.name)}</AvatarFallback>
                </Avatar>
                <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                  <Clock className="h-3 w-3" />
                  {getRelativeTime(task.dueDate)}
                </div>
              </div>
              {task.sourceType === 'ai-generated' && (
                <Badge variant="outline" className="mt-2 text-xs">
                  <Sparkles className="h-3 w-3 mr-1" />
                  AI
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

interface KanbanColumnProps {
  title: string;
  status: Task['status'];
  tasks: Task[];
  icon: React.ReactNode;
  color: string;
  onStatusChange: (taskId: string, newStatus: Task['status']) => void;
}

function KanbanColumn({ title, status, tasks, icon, color, onStatusChange }: KanbanColumnProps) {
  const [{ isOver }, drop] = useDrop(() => ({
    accept: ITEM_TYPE,
    drop: (item: { id: string; status: Task['status'] }) => {
      if (item.status !== status) {
        onStatusChange(item.id, status);
      }
    },
    collect: (monitor) => ({
      isOver: monitor.isOver(),
    }),
  }));

  return (
    <div className="flex-1 min-w-[300px]">
      <div className={`rounded-xl border-2 ${isOver ? 'border-blue-500 bg-blue-50 dark:bg-blue-950/20' : 'border-gray-200 dark:border-gray-800'} transition-colors`}>
        <div className={`p-4 border-b border-gray-200 dark:border-gray-800 ${color}`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {icon}
              <h3 className="font-semibold">{title}</h3>
            </div>
            <Badge variant="secondary">{tasks.length}</Badge>
          </div>
        </div>
        <div ref={drop} className="p-4 space-y-3 min-h-[600px]">
          {tasks.map((task) => (
            <DraggableTask key={task.id} task={task} onStatusChange={onStatusChange} />
          ))}
          {tasks.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-gray-400">
              <p className="text-sm">Görev yok</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function Tasks() {
  const [searchQuery, setSearchQuery] = useState('');
  const [tasks, setTasks] = useState(mockTasks);

  const handleStatusChange = (taskId: string, newStatus: Task['status']) => {
    setTasks((prevTasks) =>
      prevTasks.map((task) =>
        task.id === taskId ? { ...task, status: newStatus } : task
      )
    );
  };

  const filteredTasks = tasks.filter(
    (task) =>
      task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      task.description?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const todoTasks = filteredTasks.filter((t) => t.status === 'todo');
  const inProgressTasks = filteredTasks.filter((t) => t.status === 'in-progress');
  const completedTasks = filteredTasks.filter((t) => t.status === 'completed');
  const overdueTasks = filteredTasks.filter((t) => t.status === 'overdue');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-300 bg-clip-text text-transparent">
            Görevler
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Tüm görevlerinizi yönetin ve takip edin
          </p>
        </div>
        <Button className="bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 shadow-lg shadow-blue-500/20">
          <Plus className="mr-2 h-4 w-4" />
          Yeni Görev
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100 dark:bg-gray-800">
                <Clock className="h-5 w-5 text-gray-600 dark:text-gray-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{todoTasks.length}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Yapılacak</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 dark:bg-blue-900/30">
                <div className="h-5 w-5 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />
              </div>
              <div>
                <p className="text-2xl font-bold">{inProgressTasks.length}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Devam Eden</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900/30">
                <CheckCircle2 className="h-5 w-5 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{completedTasks.length}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Tamamlandı</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-gray-200 dark:border-gray-800">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-100 dark:bg-red-900/30">
                <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <p className="text-2xl font-bold">{overdueTasks.length}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">Gecikmiş</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search */}
      <Card className="border-gray-200 dark:border-gray-800">
        <CardContent className="p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              type="search"
              placeholder="Görev ara..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
        </CardContent>
      </Card>

      {/* Kanban Board */}
      <Tabs defaultValue="kanban" className="w-full">
        <TabsList>
          <TabsTrigger value="kanban">Kanban Görünümü</TabsTrigger>
          <TabsTrigger value="list">Liste Görünümü</TabsTrigger>
        </TabsList>

        <TabsContent value="kanban" className="mt-6">
          <DndProvider backend={HTML5Backend}>
            <div className="flex gap-4 overflow-x-auto pb-4">
              <KanbanColumn
                title="Yapılacaklar"
                status="todo"
                tasks={todoTasks}
                icon={<Clock className="h-5 w-5" />}
                color="bg-gray-50 dark:bg-gray-900"
                onStatusChange={handleStatusChange}
              />
              <KanbanColumn
                title="Devam Eden"
                status="in-progress"
                tasks={inProgressTasks}
                icon={<div className="h-5 w-5 rounded-full border-2 border-blue-600 border-t-transparent animate-spin" />}
                color="bg-blue-50 dark:bg-blue-950/30"
                onStatusChange={handleStatusChange}
              />
              <KanbanColumn
                title="Tamamlandı"
                status="completed"
                tasks={completedTasks}
                icon={<CheckCircle2 className="h-5 w-5 text-green-600" />}
                color="bg-green-50 dark:bg-green-950/30"
                onStatusChange={handleStatusChange}
              />
              <KanbanColumn
                title="Gecikmiş"
                status="overdue"
                tasks={overdueTasks}
                icon={<AlertCircle className="h-5 w-5 text-red-600" />}
                color="bg-red-50 dark:bg-red-950/30"
                onStatusChange={handleStatusChange}
              />
            </div>
          </DndProvider>
        </TabsContent>

        <TabsContent value="list" className="mt-6">
          <Card className="border-gray-200 dark:border-gray-800">
            <CardContent className="p-6">
              <div className="space-y-3">
                {filteredTasks.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    <CheckCircle2 className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p>Görev bulunamadı</p>
                  </div>
                ) : (
                  filteredTasks.map((task) => (
                    <div
                      key={task.id}
                      className="flex items-start gap-4 p-4 rounded-lg border border-gray-200 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                    >
                      <Avatar className="h-10 w-10">
                        <AvatarImage src={task.assignee.avatar} />
                        <AvatarFallback>{getInitials(task.assignee.name)}</AvatarFallback>
                      </Avatar>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <h4 className="font-semibold">{task.title}</h4>
                          <div className="flex items-center gap-2">
                            <Badge className={getPriorityColor(task.priority)} variant="outline">
                              {getPriorityLabel(task.priority)}
                            </Badge>
                            <Badge className={getTaskStatusColor(task.status)}>
                              {getTaskStatusLabel(task.status)}
                            </Badge>
                          </div>
                        </div>
                        {task.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                            {task.description}
                          </p>
                        )}
                        <div className="flex items-center gap-4 text-xs text-gray-600 dark:text-gray-400">
                          <span>Atanan: {task.assignee.name}</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {getRelativeTime(task.dueDate)}
                          </span>
                          {task.sourceType === 'ai-generated' && (
                            <>
                              <span>•</span>
                              <Badge variant="outline" className="h-5 text-xs">
                                <Sparkles className="h-3 w-3 mr-1" />
                                AI
                              </Badge>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
