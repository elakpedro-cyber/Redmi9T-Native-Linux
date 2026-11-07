"""Offline raw ABS -> normalized libinput matrix -> portrait output coordinates."""
def matrix(rotation=0,invert_x=False,invert_y=False):
    if rotation not in (0,90,180,270): raise ValueError('Rotation must be explicit')
    def point(x,y):
        x=1-x if invert_x else x;y=1-y if invert_y else y
        return {0:(x,y),90:(1-y,x),180:(1-x,1-y),270:(y,1-x)}[rotation]
    x0,y0=point(0,0);x1,y1=point(1,0);x2,y2=point(0,1)
    return (x1-x0,x2-x0,x0,y1-y0,y2-y0,y0)
def transform(x,y,bounds=(0,1079,0,2339),rotation=0,invert_x=False,invert_y=False,width=1080,height=2340):
    xmin,xmax,ymin,ymax=bounds
    if xmax<=xmin or ymax<=ymin or width<2 or height<2: raise ValueError('Invalid measured geometry')
    if not xmin<=x<=xmax or not ymin<=y<=ymax: raise ValueError('Out-of-range contact')
    u,v=(x-xmin)/(xmax-xmin),(y-ymin)/(ymax-ymin)
    a,b,c,d,e,f=matrix(rotation,invert_x,invert_y)
    return round((a*u+b*v+c)*(width-1)),round((d*u+e*v+f)*(height-1))
