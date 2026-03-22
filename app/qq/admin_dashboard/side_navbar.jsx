import { View, Text, StyleSheet, TouchableOpacity, useWindowDimensions } from 'react-native'
import { useRouter } from 'expo-router'
import { MaterialCommunityIcons } from '@expo/vector-icons'

const NAV_ITEMS = [
  { label: 'Dashboard', icon: 'home-outline', route: '/qq/admin_dashboard/ad_index' },
  { label: 'Appointments', icon: 'calendar-outline', route: '/qq/admin_dashboard/appoint' },
  { label: 'Queue Management', icon: 'account-group-outline', route: '/qq/admin_dashboard/queue' },
  { label: 'Priority Verification', icon: 'check-decagram-outline', route: '/qq/admin_dashboard/prio' },
  { label: 'Walk-In Registration', icon: 'account-plus-outline', route: '/qq/admin_dashboard/walk_in' },
  { label: 'Services', icon: 'clipboard-text-outline', route: '/qq/admin_dashboard/services' },
  { label: 'Reports', icon: 'chart-bar', route: '/qq/admin_dashboard/reports' },
  { label: 'Announcements', icon: 'bullhorn-outline', route: '/qq/admin_dashboard/announcements' },
  { label: 'Settings', icon: 'cog-outline', route: '/qq/admin_dashboard/settings' },
]

const SideNavbar = ({ activeItem = 'Dashboard', onItemPress }) => {
  const router = useRouter()
  const { width } = useWindowDimensions()
  const isCompact = width < 1100

  return (
    <View style={[styles.sidebar, isCompact && styles.sidebarCompact]}>
      <View style={styles.brandCard}>
        <View style={styles.logoTile}>
          <Text style={styles.logoQQYellow}>Q</Text>
          <Text style={styles.logoQQRed}>Q</Text>
        </View>
        <View>
          <Text style={styles.brandTitle}>QQ Admin</Text>
          <Text style={styles.brandSubtitle}>Management</Text>
        </View>
      </View>

      <View style={[styles.navList, isCompact && styles.navListCompact]}>
        {NAV_ITEMS.map((item) => {
          const isActive = item.label === activeItem

          return (
            <TouchableOpacity
              key={item.label}
              activeOpacity={0.8}
              style={[styles.navItem, isActive && styles.navItemActive, isCompact && styles.navItemCompact]}
              onPress={() => {
                onItemPress?.(item)

                if (item.route && item.label !== activeItem) {
                  router.push(item.route)
                }
              }}
            >
              <MaterialCommunityIcons
                name={item.icon}
                size={24}
                color="#4B5563"
                style={styles.navIcon}
              />
              <Text style={styles.navLabel}>{item.label}</Text>
            </TouchableOpacity>
          )
        })}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  sidebar: {
    width: 420,
    backgroundColor: '#FFFFFF',
    borderRightWidth: 1,
    borderColor: '#111827',
  },
  sidebarCompact: {
    width: '100%',
    borderRightWidth: 0,
    borderBottomWidth: 1,
  },
  brandCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
    paddingHorizontal: 24,
    paddingVertical: 18,
    borderBottomWidth: 1,
    borderColor: '#111827',
  },
  logoTile: {
    width: 80,
    height: 80,
    borderRadius: 22,
    backgroundColor: '#1D397A',
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
  logoQQYellow: {
    fontSize: 30,
    fontWeight: '900',
    color: '#FFD14C',
  },
  logoQQRed: {
    fontSize: 30,
    fontWeight: '900',
    color: '#F44336',
    marginLeft: 2,
  },
  brandTitle: {
    fontSize: 22,
    fontWeight: '800',
    color: '#000000',
  },
  brandSubtitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#6B6871',
  },
  navList: {
    backgroundColor: '#FFFFFF',
  },
  navListCompact: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
  navItem: {
    minHeight: 88,
    borderBottomWidth: 1,
    borderColor: '#111827',
    paddingHorizontal: 24,
    flexDirection: 'row',
    alignItems: 'center',
  },
  navItemCompact: {
    width: '50%',
  },
  navItemActive: {
    backgroundColor: '#6099DC',
  },
  navIcon: {
    marginRight: 18,
  },
  navLabel: {
    fontSize: 22,
    fontWeight: '600',
    color: '#111111',
    flexShrink: 1,
  },
})

export default SideNavbar
