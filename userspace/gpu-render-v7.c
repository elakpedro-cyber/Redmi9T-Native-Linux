#include <EGL/egl.h>
#include <EGL/eglext.h>
#include <GLES2/gl2.h>
#include <gbm.h>
#include <xf86drm.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x); return 1; } } while (0)

static GLuint shader(GLenum type, const char *source)
{
    GLuint object=glCreateShader(type);
    GLint ok=0;
    glShaderSource(object,1,&source,NULL);
    glCompileShader(object);
    glGetShaderiv(object,GL_COMPILE_STATUS,&ok);
    if (!ok) { char log[1024]; glGetShaderInfoLog(object,sizeof(log),NULL,log); fprintf(stderr,"%s\n",log); exit(1); }
    return object;
}

int main(int argc, char **argv)
{
    CHECK(argc==2);
    CHECK(strncmp(argv[1],"/dev/dri/renderD",16)==0);
    int fd=open(argv[1],O_RDWR|O_CLOEXEC);
    CHECK(fd>=0);
    drmVersionPtr version=drmGetVersion(fd);
    CHECK(version && strcmp(version->name,"msm")==0);
    printf("DRM=%s %d.%d.%d\n",version->name,version->version_major,version->version_minor,version->version_patchlevel);
    struct gbm_device *gbm=gbm_create_device(fd);
    CHECK(gbm);
    PFNEGLGETPLATFORMDISPLAYEXTPROC get_display=(void *)eglGetProcAddress("eglGetPlatformDisplayEXT");
    CHECK(get_display);
    EGLDisplay display=get_display(EGL_PLATFORM_GBM_KHR,gbm,NULL);
    EGLint major,minor;
    CHECK(eglInitialize(display,&major,&minor));
    CHECK(eglBindAPI(EGL_OPENGL_ES_API));
    CHECK((major>1 || minor>=5) || strstr(eglQueryString(display,EGL_EXTENSIONS),"EGL_KHR_surfaceless_context"));
    EGLint attributes[]={EGL_SURFACE_TYPE,0,EGL_RENDERABLE_TYPE,EGL_OPENGL_ES2_BIT,EGL_RED_SIZE,8,EGL_GREEN_SIZE,8,EGL_BLUE_SIZE,8,EGL_ALPHA_SIZE,8,EGL_NONE};
    EGLConfig config;EGLint count;
    CHECK(eglChooseConfig(display,attributes,&config,1,&count) && count==1);
    EGLint context_attributes[]={EGL_CONTEXT_CLIENT_VERSION,2,EGL_NONE};
    EGLContext context=eglCreateContext(display,config,EGL_NO_CONTEXT,context_attributes);
    CHECK(context!=EGL_NO_CONTEXT);
    CHECK(eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,context));
    const char *renderer=(const char *)glGetString(GL_RENDERER);
    CHECK(renderer);
    printf("EGL=%d.%d GLES=%s renderer=%s\n",major,minor,glGetString(GL_VERSION),renderer);
    CHECK(strstr(renderer,"610") && !strstr(renderer,"llvmpipe") && !strstr(renderer,"softpipe"));
    GLuint texture,framebuffer;
    glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_NEAREST);
    glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
    glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,16,16,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
    glGenFramebuffers(1,&framebuffer);glBindFramebuffer(GL_FRAMEBUFFER,framebuffer);
    glFramebufferTexture2D(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
    CHECK(glCheckFramebufferStatus(GL_FRAMEBUFFER)==GL_FRAMEBUFFER_COMPLETE);
    GLuint program=glCreateProgram();
    glAttachShader(program,shader(GL_VERTEX_SHADER,"attribute vec2 p; void main(){gl_Position=vec4(p,0.,1.);}"));
    glAttachShader(program,shader(GL_FRAGMENT_SHADER,"precision mediump float; void main(){gl_FragColor=vec4(.25,.5,.75,1.);}"));
    glBindAttribLocation(program,0,"p");glLinkProgram(program);
    GLint linked;glGetProgramiv(program,GL_LINK_STATUS,&linked);CHECK(linked);
    glUseProgram(program);glViewport(0,0,16,16);glDisable(GL_DITHER);
    GLfloat vertices[]={-1,-1,3,-1,-1,3};
    glVertexAttribPointer(0,2,GL_FLOAT,GL_FALSE,0,vertices);glEnableVertexAttribArray(0);
    glClearColor(0,0,0,0);glClear(GL_COLOR_BUFFER_BIT);glDrawArrays(GL_TRIANGLES,0,3);glFinish();
    unsigned char pixels[16*16*4];
    glReadPixels(0,0,16,16,GL_RGBA,GL_UNSIGNED_BYTE,pixels);
    CHECK(glGetError()==GL_NO_ERROR);
    const int expected[]={64,128,191,255};
    for (size_t i=0;i<sizeof(pixels);i++) CHECK(abs((int)pixels[i]-expected[i%4])<=1);
    FILE *out=fopen("/tmp/gpu-render-v7.rgba","wb");CHECK(out);
    CHECK(fwrite(pixels,1,sizeof(pixels),out)==sizeof(pixels));CHECK(fclose(out)==0);
    puts("LEMON_GPU_V7_RENDER_PASS: GLES shader draw and 256 RGBA pixels verified; output /tmp/gpu-render-v7.rgba");
    glDeleteFramebuffers(1,&framebuffer);glDeleteTextures(1,&texture);glDeleteProgram(program);
    eglMakeCurrent(display,EGL_NO_SURFACE,EGL_NO_SURFACE,EGL_NO_CONTEXT);
    eglDestroyContext(display,context);eglTerminate(display);
    gbm_device_destroy(gbm);drmFreeVersion(version);close(fd);
    return 0;
}
