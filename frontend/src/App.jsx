import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import {
  Layout, Menu, Typography, theme, Select, Space,
  Modal, Form, Input, Button, Table, Tag, Tooltip, message, Popconfirm,
} from 'antd'
import {
  DashboardOutlined, CloudDownloadOutlined, FilePdfOutlined,
  AuditOutlined, FileSearchOutlined, DatabaseOutlined,
  PlusOutlined, DeleteOutlined, CheckCircleOutlined, ApiOutlined,
  EditOutlined, UserAddOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons'

import Dashboard          from './pages/Dashboard'
import Importacao         from './pages/Importacao'
import Informes           from './pages/Informes'
import Conferencia        from './pages/Conferencia'
import ConferenciaFolha   from './pages/ConferenciaFolha'
import ComparacaoIRPF          from './pages/ComparacaoIRPF'
import PendenciasEsocial       from './pages/PendenciasEsocial'
import ConferenciaFuncionario  from './pages/ConferenciaFuncionario'
import {
  getConexoes, ativarConexao, adicionarConexao,
  removerConexao, testarConexao, atualizarConexao,
  getNomesOverride, salvarNomeOverride, removerNomeOverride,
} from './api'

const { Sider, Header, Content } = Layout
const { Text } = Typography

const menuItems = [
  { key: '/',            icon: <DashboardOutlined />,     label: 'Dashboard' },
  { key: '/importacao',  icon: <CloudDownloadOutlined />, label: 'Importação' },
  { key: '/informes',    icon: <FilePdfOutlined />,       label: 'Informes' },
  { key: '/conferencia',       icon: <AuditOutlined />,              label: 'Conferência' },
  { key: '/conferencia-folha', icon: <AuditOutlined />,              label: 'Conf. Folha×eSocial' },
  { key: '/conferencia-func',  icon: <AuditOutlined />,              label: 'Conf. por Funcionário' },
  { key: '/pendencias',        icon: <ExclamationCircleOutlined />,  label: 'Pendências eSocial' },
  { key: '/irpf',              icon: <FileSearchOutlined />,         label: 'Comparar IRPF' },
]

// ── Modal de gerenciar conexões ────────────────────────────────────────────────
function GerenciarConexoes({ open, onClose, onMudou }) {
  const [conexoes, setConexoes]       = useState([])
  const [ativa, setAtiva]             = useState(null)
  const [adicionando, setAdicionando] = useState(false)
  const [editandoId, setEditandoId]   = useState(null)
  const [testando, setTestando]       = useState({})
  const [form]     = Form.useForm()
  const [formEdit] = Form.useForm()

  const carregar = () =>
    getConexoes().then(r => { setConexoes(r.data.conexoes); setAtiva(r.data.ativa) })

  useEffect(() => { if (open) carregar() }, [open])

  const handleAtivar = (id) => {
    ativarConexao(id)
      .then(() => { message.success('Banco alterado!'); carregar(); onMudou() })
      .catch(e => message.error(e.response?.data?.detail || 'Erro ao conectar'))
  }

  const handleTestar = (id) => {
    setTestando(p => ({ ...p, [id]: true }))
    testarConexao(id)
      .then(r => message.info(r.data.mensagem))
      .catch(e => message.error(e.response?.data?.detail || 'Falha na conexão'))
      .finally(() => setTestando(p => ({ ...p, [id]: false })))
  }

  const handleRemover = (id) => {
    removerConexao(id).then(() => carregar())
  }

  const handleAdicionar = (vals) => {
    adicionarConexao(vals)
      .then(() => { message.success('Conexão adicionada!'); form.resetFields(); setAdicionando(false); carregar() })
      .catch(e => message.error(e.response?.data?.detail || 'Erro'))
  }

  const handleAbrirEditar = (conn) => {
    setEditandoId(conn.id)
    setAdicionando(false)
    formEdit.setFieldsValue({ ...conn, pwd: '' })
  }

  const handleSalvarEdicao = (vals) => {
    atualizarConexao(editandoId, { ...vals, id: editandoId })
      .then(() => { message.success('Conexão atualizada!'); setEditandoId(null); carregar(); onMudou() })
      .catch(e => message.error(e.response?.data?.detail || 'Erro ao salvar'))
  }

  const cols = [
    { title: 'Nome',     dataIndex: 'nome',     key: 'nome' },
    { title: 'Servidor', dataIndex: 'server',   key: 'server' },
    { title: 'Banco',    dataIndex: 'database', key: 'database' },
    {
      title: 'Status', key: 'status', width: 90, align: 'center',
      render: (_, r) => r.id === ativa
        ? <Tag color="green" icon={<CheckCircleOutlined />}>Ativa</Tag>
        : null,
    },
    {
      title: 'Ações', key: 'acoes', width: 200, align: 'center',
      render: (_, r) => (
        <Space size={4}>
          <Tooltip title="Testar conexão">
            <Button size="small" icon={<ApiOutlined />} loading={testando[r.id]}
              onClick={() => handleTestar(r.id)} />
          </Tooltip>
          <Tooltip title="Editar pastas e dados">
            <Button size="small" icon={<EditOutlined />}
              onClick={() => handleAbrirEditar(r)} />
          </Tooltip>
          {r.id !== ativa && (
            <Button size="small" type="primary" ghost onClick={() => handleAtivar(r.id)}>
              Usar
            </Button>
          )}
          <Popconfirm title="Remover esta conexão?" onConfirm={() => handleRemover(r.id)}
            okText="Sim" cancelText="Não">
            <Button size="small" danger icon={<DeleteOutlined />} disabled={r.id === ativa} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const camposForm = (isEdit) => <>
    {!isEdit && (
      <Form.Item label="ID único" name="id" rules={[{ required: true }]}
        extra="Identificador interno, sem espaços (ex: kiko)">
        <Input placeholder="ex: empresa2" />
      </Form.Item>
    )}
    <Form.Item label="Nome exibição" name="nome" rules={[{ required: true }]}>
      <Input placeholder="ex: Empresa Beta" />
    </Form.Item>
    <Form.Item label="Servidor" name="server" rules={[{ required: true }]}>
      <Input placeholder="ex: 100.110.194.113" />
    </Form.Item>
    <Form.Item label="Banco de dados" name="database" rules={[{ required: true }]}>
      <Input placeholder="ex: folha_kiko" />
    </Form.Item>
    <Form.Item label="Usuário" name="uid" rules={[{ required: true }]}>
      <Input />
    </Form.Item>
    <Form.Item label="Senha" name="pwd"
      extra={isEdit ? 'Deixe em branco para manter a senha atual' : undefined}
      rules={isEdit ? [] : [{ required: true }]}>
      <Input.Password />
    </Form.Item>
    <Form.Item label="Pasta XML S-1210" name="pasta_xml_s1210"
      extra="Pasta raiz com subpastas por empresa">
      <Input placeholder={'ex: D:\\xmls\\empresa\\s1210'} />
    </Form.Item>
    <Form.Item label="Pasta XML S-1200 (retornos)" name="pasta_xml_s1200">
      <Input placeholder={'ex: D:\\xmls\\empresa\\retornos\\12345678000100'} />
    </Form.Item>
    <Form.Item label="Pasta Informes PDF" name="pasta_informes">
      <Input placeholder={'ex: D:\\informes\\empresa'} />
    </Form.Item>
  </>

  return (
    <Modal
      open={open} onCancel={onClose} title="Gerenciar Conexões de Banco"
      footer={null} width={700}
    >
      <Table dataSource={conexoes} columns={cols} rowKey="id" size="small"
        pagination={false} style={{ marginBottom: 16 }} />

      {editandoId ? (
        <Form form={formEdit} layout="vertical" onFinish={handleSalvarEdicao}>
          <Text strong style={{ display: 'block', marginBottom: 12 }}>
            Editando: <Text code>{editandoId}</Text>
          </Text>
          {camposForm(true)}
          <Space>
            <Button type="primary" htmlType="submit">Salvar</Button>
            <Button onClick={() => setEditandoId(null)}>Cancelar</Button>
          </Space>
        </Form>
      ) : adicionando ? (
        <Form form={form} layout="vertical" onFinish={handleAdicionar}
          initialValues={{ uid: 'sa' }}>
          {camposForm(false)}
          <Space>
            <Button type="primary" htmlType="submit">Salvar e Testar</Button>
            <Button onClick={() => setAdicionando(false)}>Cancelar</Button>
          </Space>
        </Form>
      ) : (
        <Button icon={<PlusOutlined />} onClick={() => setAdicionando(true)}>
          Adicionar Conexão
        </Button>
      )}
    </Modal>
  )
}

// ── Modal de nomes override ────────────────────────────────────────────────────
function NomesOverride({ open, onClose }) {
  const [nomes, setNomes]       = useState([])
  const [adicionando, setAd]    = useState(false)
  const [form]                  = Form.useForm()

  const carregar = () => getNomesOverride().then(r => setNomes(r.data))
  useEffect(() => { if (open) carregar() }, [open])

  const handleSalvar = (vals) => {
    salvarNomeOverride({ ...vals, cpf: vals.cpf.replace(/\D/g,'') })
      .then(() => { message.success('Nome salvo!'); form.resetFields(); setAd(false); carregar() })
      .catch(e => message.error(e.response?.data?.detail || 'Erro'))
  }

  const handleRemover = (cpf) => {
    removerNomeOverride(cpf).then(() => carregar())
  }

  const cols = [
    { title: 'CPF',  dataIndex: 'cpf',  key: 'cpf', width: 130,
      render: v => `${v.slice(0,3)}.${v.slice(3,6)}.${v.slice(6,9)}-${v.slice(9)}` },
    { title: 'Nome', dataIndex: 'nome', key: 'nome' },
    { title: 'Obs',  dataIndex: 'obs',  key: 'obs', ellipsis: true },
    { title: '', key: 'del', width: 48, align: 'center',
      render: (_, r) => (
        <Popconfirm title="Remover?" onConfirm={() => handleRemover(r.cpf)} okText="Sim" cancelText="Não">
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  return (
    <Modal open={open} onCancel={onClose} title="Nomes para Beneficiários Não Identificados"
      footer={null} width={680}>
      <Text type="secondary" style={{ display: 'block', marginBottom: 12, fontSize: 12 }}>
        CPFs encontrados no eSocial mas ausentes do cadastro (FOLFUN).
        Cadastre o nome para que apareça no informe em vez de "NAO IDENTIFICADO".
      </Text>
      <Table dataSource={nomes} columns={cols} rowKey="cpf" size="small"
        pagination={false} style={{ marginBottom: 12 }} />

      {adicionando ? (
        <Form form={form} layout="inline" onFinish={handleSalvar}>
          <Form.Item name="cpf" rules={[{ required: true, min: 11, message: 'CPF 11 dígitos' }]}>
            <Input placeholder="CPF (11 dígitos)" maxLength={14} style={{ width: 140 }} />
          </Form.Item>
          <Form.Item name="nome" rules={[{ required: true }]} style={{ flex: 1 }}>
            <Input placeholder="Nome completo" />
          </Form.Item>
          <Form.Item name="obs">
            <Input placeholder="Obs (opcional)" style={{ width: 160 }} />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">Salvar</Button>
              <Button onClick={() => setAd(false)}>Cancelar</Button>
            </Space>
          </Form.Item>
        </Form>
      ) : (
        <Button icon={<PlusOutlined />} onClick={() => setAd(true)}>Adicionar nome</Button>
      )}
    </Modal>
  )
}

// ── Layout principal ──────────────────────────────────────────────────────────
function AppLayout() {
  const navigate  = useNavigate()
  const location  = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const { token } = theme.useToken()
  const [conexoes, setConexoes]   = useState([])
  const [ativa, setAtiva]         = useState(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [nomesOpen, setNomesOpen] = useState(false)

  const carregarConexoes = () =>
    getConexoes().then(r => { setConexoes(r.data.conexoes); setAtiva(r.data.ativa) })
      .catch(() => {})

  useEffect(() => { carregarConexoes() }, [])

  const handleTrocarBanco = (id) => {
    ativarConexao(id)
      .then(() => { setAtiva(id); message.success('Banco alterado!') })
      .catch(e => message.error(e.response?.data?.detail || 'Erro ao conectar'))
  }

  const paginaAtual = menuItems.find(m => m.key === location.pathname)
  const nomeAtiva   = conexoes.find(c => c.id === ativa)?.nome || '...'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed}
        style={{ background: token.colorBgContainer }} width={210}>
        <div style={{
          height: 60, display: 'flex', alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 14px',
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          overflow: 'hidden',
        }}>
          {collapsed
            ? <span style={{ fontSize: 20 }}>🌾</span>
            : <div>
                <Text strong style={{ fontSize: 13, display: 'block' }}>🌾 Agronil</Text>
                <Text type="secondary" style={{ fontSize: 10 }}>Informe de Rendimento</Text>
              </div>
          }
        </div>
        <Menu mode="inline" selectedKeys={[location.pathname]} items={menuItems}
          onClick={({ key }) => navigate(key)} style={{ borderRight: 0, marginTop: 8 }} />
      </Sider>

      <Layout>
        <Header style={{
          background: token.colorBgContainer,
          borderBottom: `1px solid ${token.colorBorderSecondary}`,
          padding: '0 20px', display: 'flex', alignItems: 'center',
          justifyContent: 'space-between', height: 50, lineHeight: 'normal',
        }}>
          <Text strong style={{ fontSize: 14 }}>{paginaAtual?.label || ''}</Text>

          <Space size={8}>
            <DatabaseOutlined style={{ color: token.colorPrimary }} />
            <Select
              value={ativa}
              onChange={handleTrocarBanco}
              size="small"
              style={{ minWidth: 160 }}
              options={conexoes.map(c => ({ value: c.id, label: c.nome }))}
              placeholder="Banco..."
            />
            <Tooltip title="Gerenciar conexões">
              <Button size="small" icon={<PlusOutlined />}
                onClick={() => setModalOpen(true)} />
            </Tooltip>
            <Tooltip title="Nomes de beneficiários não identificados">
              <Button size="small" icon={<UserAddOutlined />}
                onClick={() => setNomesOpen(true)} />
            </Tooltip>
            <Text type="secondary" style={{ fontSize: 11 }}>
              Ano 2025 · Ex. 2026
            </Text>
          </Space>
        </Header>

        <Content key={ativa || 'default'} style={{ background: token.colorBgLayout, minHeight: 'calc(100vh - 50px)' }}>
          <Routes>
            <Route path="/"            element={<Dashboard />} />
            <Route path="/importacao"  element={<Importacao />} />
            <Route path="/informes"    element={<Informes />} />
            <Route path="/conferencia"       element={<Conferencia />} />
            <Route path="/conferencia-folha" element={<ConferenciaFolha />} />
            <Route path="/conferencia-func"  element={<ConferenciaFuncionario />} />
            <Route path="/pendencias"        element={<PendenciasEsocial />} />
            <Route path="/irpf"              element={<ComparacaoIRPF />} />
          </Routes>
        </Content>
      </Layout>

      <GerenciarConexoes
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onMudou={() => { carregarConexoes(); setModalOpen(false) }}
      />
      <NomesOverride open={nomesOpen} onClose={() => setNomesOpen(false)} />
    </Layout>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
